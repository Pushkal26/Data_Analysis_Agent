"""
Chat Service
============
Handles chat operations and LangGraph integration.

This service:
1. Receives chat messages
2. Retrieves file context (with caching)
3. Runs the LangGraph analysis pipeline
4. Caches and saves results to database
5. Returns formatted response
"""

import sys
import time
import math
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

# Add langgraph to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.models import (
    Session,
    UploadedFile,
    ChatMessage,
    AnalysisResult,
    MessageRole,
    AnalysisStatus,
)
from app.core.cache import cache_service

logger = structlog.get_logger(__name__)


class ChatService:
    """
    Service for handling chat operations.
    
    Responsibilities:
    - Process chat messages
    - Run LangGraph analysis
    - Store messages and results
    - Cache frequently accessed data
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    def _parse_intent(self, intent_value: Any) -> Optional[str]:
        """Parse intent value, handling cases where LLM returns multiple intents."""
        if not intent_value:
            return None
        
        intent_str = str(intent_value)
        
        # If contains pipes, take the first one
        if "|" in intent_str:
            intent_str = intent_str.split("|")[0].strip()
        
        # Validate it's a known intent
        valid_intents = ["query", "aggregate", "compare", "trend", "forecast", "anomaly", "correlation"]
        if intent_str.lower() in valid_intents:
            return intent_str.lower()
        
        return None
    
    async def get_files_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all files for a session as dicts (with caching)."""
        # Try cache first
        cached = await cache_service.get_session_files(session_id)
        if cached:
            logger.debug("Files cache hit", session_id=session_id)
            return cached
        
        session = await self.get_session(session_id)
        if not session:
            return []
        
        result = await self.db.execute(
            select(UploadedFile).where(UploadedFile.session_id == session.id)
        )
        files = result.scalars().all()
        
        files_data = [
            {
                "id": f.id,
                "filename": f.filename,
                "filepath": f.filepath,
                "time_period": f.time_period,
                "time_period_type": f.time_period_type,
                "row_count": f.row_count,
                "columns": f.columns,
                "numeric_columns": f.numeric_columns,
                "categorical_columns": f.categorical_columns,
                "date_columns": f.date_columns,
                "schema": f.schema,
                "sample_data": f.sample_data,
            }
            for f in files
        ]
        
        # Cache the result
        await cache_service.set_session_files(session_id, files_data)
        logger.debug("Files cached", session_id=session_id, file_count=len(files_data))
        
        return files_data
    
    async def get_chat_history(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent chat history for context."""
        session = await self.get_session(session_id)
        if not session:
            return []
        
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        
        # Reverse to get chronological order
        return [
            {"role": m.role.value, "content": m.content}
            for m in reversed(messages)
        ]
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """
        Sanitize data for JSON serialization by replacing NaN and Infinity with None.
        
        PostgreSQL JSON columns don't accept NaN or Infinity values.
        """
        if data is None:
            return None
        
        if isinstance(data, dict):
            return {key: self._sanitize_json_data(value) for key, value in data.items()}
        
        if isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        
        if isinstance(data, float):
            if math.isnan(data) or math.isinf(data):
                return None
        
        return data
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        analysis_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Save a chat message."""
        session = await self.get_session(session_id)
        if not session:
            # Create session if it doesn't exist
            session = Session(session_id=session_id)
            self.db.add(session)
            await self.db.flush()
        
        message = ChatMessage(
            session_id=session.id,
            role=MessageRole(role),
            content=content,
            analysis_id=analysis_id,
            metadata_json=metadata or {},
        )
        self.db.add(message)
        await self.db.flush()
        
        return message
    
    async def save_analysis_result(
        self,
        session_id: str,
        user_query: str,
        result: Dict[str, Any],
    ) -> AnalysisResult:
        """Save analysis result to database."""
        session = await self.get_session(session_id)
        if not session:
            session = Session(session_id=session_id)
            self.db.add(session)
            await self.db.flush()
        
        # Determine status
        if result.get("errors"):
            status = AnalysisStatus.FAILED
        elif result.get("final_response"):
            status = AnalysisStatus.COMPLETED
        else:
            status = AnalysisStatus.COMPLETED
        
        # Get execution time
        exec_result = result.get("execution_result") or {}
        execution_time = exec_result.get("execution_time_ms") if exec_result else None
        
        analysis = AnalysisResult(
            session_id=session.id,
            status=status,
            user_query=user_query,
            intent=self._parse_intent(result.get("intent")),
            operation_type=result.get("operation_type"),
            files_used=result.get("files_to_use", []),
            plan=self._sanitize_json_data(result.get("plan")),
            generated_code=result.get("generated_code"),
            code_valid=result.get("code_valid", False),
            result_data=self._sanitize_json_data(result.get("result_data")),
            error_message="; ".join(result.get("errors", [])) if result.get("errors") else None,
            execution_time_ms=execution_time,
            explanation=result.get("explanation"),
            recommendations=result.get("recommendations", []),
            node_history=result.get("node_history", []),
            langgraph_trace=None,  # Could store full trace for debugging
        )
        
        self.db.add(analysis)
        await self.db.flush()
        
        return analysis
    
    async def process_message(
        self,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response.
        
        This is the main entry point for chat:
        1. Save user message
        2. Check cache for identical query
        3. Get file context
        4. Run LangGraph
        5. Cache and save result
        6. Return response
        """
        start_time = time.time()
        
        # Save user message
        await self.save_message(session_id, "user", message)
        
        # Get files for this session
        files = await self.get_files_for_session(session_id)
        
        if not files:
            # No files uploaded
            response_text = (
                "📁 No data files have been uploaded yet.\n\n"
                "Please upload your CSV or Excel files first, then I can help you analyze them."
            )
            await self.save_message(session_id, "assistant", response_text)
            
            return {
                "status": "success",
                "response": response_text,
                "analysis": None,
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
        
        # Check cache for identical query
        file_ids = [f["id"] for f in files]
        cached_result = await cache_service.get_analysis_result(session_id, message, file_ids)
        
        if cached_result:
            logger.info("Analysis cache hit", session_id=session_id, query=message[:30])
            
            # Still save the message and reference
            response_text = cached_result.get("final_response") or cached_result.get("explanation") or "Analysis complete."
            await self.save_message(session_id, "assistant", response_text + "\n\n*[Cached result]*")
            
            return {
                "status": "success",
                "response": response_text,
                "analysis": {
                    "id": cached_result.get("analysis_id"),
                    "intent": cached_result.get("intent"),
                    "operation_type": cached_result.get("operation_type"),
                    "files_used": cached_result.get("files_to_use", []),
                    "result_data": cached_result.get("result_data"),
                    "recommendations": cached_result.get("recommendations", []),
                },
                "cached": True,
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
        
        # Get chat history for context
        chat_history = await self.get_chat_history(session_id)
        
        # Run LangGraph analysis
        try:
            from pipeline import run_analysis_sync
            
            logger.info(
                "Running analysis",
                session_id=session_id,
                query=message[:50],
                file_count=len(files),
            )
            
            result = run_analysis_sync(
                session_id=session_id,
                user_query=message,
                available_files=files,
                chat_history=chat_history,
            )
            
            # Ensure result is a dict
            if result is None:
                result = {"errors": ["Analysis returned None"], "final_response": "Unable to complete analysis"}
            
            # Save analysis result
            analysis = await self.save_analysis_result(
                session_id=session_id,
                user_query=message,
                result=result,
            )
            
            # Add analysis ID to result for caching
            result["analysis_id"] = analysis.id
            
            # Cache the result
            await cache_service.set_analysis_result(session_id, message, file_ids, result)
            
            # Get response text
            response_text = result.get("final_response") or result.get("explanation") or "Analysis complete."
            
            # Save assistant message
            await self.save_message(
                session_id, 
                "assistant", 
                response_text,
                analysis_id=analysis.id,
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(
                "Analysis completed",
                session_id=session_id,
                analysis_id=analysis.id,
                processing_time_ms=processing_time,
            )
            
            return {
                "status": "success",
                "response": response_text,
                "analysis": {
                    "id": analysis.id,
                    "intent": result.get("intent"),
                    "operation_type": result.get("operation_type"),
                    "files_used": result.get("files_to_use", []),
                    "result_data": result.get("result_data"),
                    "recommendations": result.get("recommendations", []),
                },
                "cached": False,
                "processing_time_ms": processing_time,
            }
            
        except Exception as e:
            logger.error(
                "Analysis failed",
                session_id=session_id,
                error=str(e),
            )
            
            # Handle errors
            error_message = f"I encountered an error while analyzing your data: {str(e)}"
            
            await self.save_message(session_id, "assistant", error_message)
            
            return {
                "status": "error",
                "response": error_message,
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
