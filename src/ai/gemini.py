import json
import logging
from typing import Any, Dict, List, Optional, Type

import google.generativeai as genai
from pydantic import BaseModel, create_model

from src.core.config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        if not config.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. AI features will fail.")
        else:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model_name = config.DEFAULT_MODEL
            self.model = genai.GenerativeModel(self.model_name)

    def set_model(self, model_name: str):
        """Switch the active Gemini model."""
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Switched AI model to: {model_name}")

    async def generate_title(self, objective: str, content: str) -> str:
        """
        Generate a concise session title based on objective and content.
        """
        prompt = f"""
        Objective: "{objective}"
        Content Snippet:
        {content[:1000]}...
        
        Generate a very concise (2-4 words) session title.
        It does not need to be grammatically correct, just descriptive and short.
        Example: "Basketball Stats Scrape" or "Nike Shoes Price"
        
        Return ONLY the title text.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return "Untitled Session"

    async def generate_schema(self, objective: str) -> Type[BaseModel]:
        """
        Generate a Pydantic model schema based on the user's objective.
        """
        prompt = f"""
        You are an expert data engineer.
        Objective: "{objective}"
        
        Create a JSON schema that represents the data structure needed to satisfy this objective.
        The schema should be a list of items if the objective implies extracting multiple records.
        
        Return ONLY the JSON schema.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            schema_json = self._clean_json_response(response.text)
            # For now, we'll return a dynamic model based on this JSON
            # In a real implementation, we might want to use more robust schema generation
            # or just return the dict to be used by the extractor.
            # Let's return a simple dict for now to represent the schema structure.
            return json.loads(schema_json)
        except Exception as e:
            logger.error(f"Schema generation failed: {e}")
            raise

    async def analyze_relevance(
        self, objective: str, content: str, url: str
    ) -> Dict[str, Any]:
        """
        Analyze if the page content is relevant to the objective and extract links.
        """
        prompt = f"""
        Objective: "{objective}"
        URL: "{url}"
        Content Snippet:
        {content[:5000]}... (truncated)
        
        1. Is this page relevant to the objective? (true/false)
        2. If relevant, explain why briefly.
        3. Identify up to 5 most relevant links to follow next.
        
        Return JSON format:
        {{
            "is_relevant": boolean,
            "reason": "string",
            "next_urls": ["url1", "url2"]
        }}
        """

        response = None
        try:
            response = await self.model.generate_content_async(prompt)
            cleaned_text = self._clean_json_response(response.text)
            return json.loads(cleaned_text)
        except Exception as e:
            logger.error(f"Relevance analysis failed: {e}")
            # Log the raw response for debugging
            if response:
                try:
                    logger.debug(f"Raw response: {response.text}")
                except Exception:
                    pass
            return {"is_relevant": False, "reason": "Error", "next_urls": []}

    async def extract_data(
        self, content: str, schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract structured data from content based on the schema.
        """
        prompt = f"""
        Extract data from the following content matching this schema:
        {json.dumps(schema, indent=2)}
        
        Content:
        {content[:10000]}... (truncated)
        
        Return a JSON object containing the extracted data.
        """

        response = None
        try:
            response = await self.model.generate_content_async(prompt)
            cleaned_text = self._clean_json_response(response.text)
            result = json.loads(cleaned_text)
            # Ensure it's a list
            if isinstance(result, dict):
                return [result]
            return result
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            if response:
                try:
                    logger.debug(f"Raw response: {response.text}")
                except Exception:
                    pass
            return []

    def _clean_json_response(self, text: str) -> str:
        """Helper to clean markdown code blocks from JSON response."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Find the first '{' or '[' and last '}' or ']'
        # This handles both object and list returns
        start_obj = text.find("{")
        start_list = text.find("[")

        start = -1
        if start_obj != -1 and start_list != -1:
            start = min(start_obj, start_list)
        elif start_obj != -1:
            start = start_obj
        elif start_list != -1:
            start = start_list

        end_obj = text.rfind("}")
        end_list = text.rfind("]")

        end = -1
        if end_obj != -1 and end_list != -1:
            end = max(end_obj, end_list)
        elif end_obj != -1:
            end = end_obj
        elif end_list != -1:
            end = end_list

        if start != -1 and end != -1:
            text = text[start : end + 1]

        return text
