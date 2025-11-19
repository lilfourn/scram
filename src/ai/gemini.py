import json
import logging
import base64
from typing import Any, Dict, List, Type, Optional

import google.generativeai as genai
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.core.config import config
from src.ai.prompts import (
    ORCHESTRATOR_INSTRUCTION,
    FAST_AGENT_INSTRUCTION,
    get_seed_analysis_prompt,
    get_title_generation_prompt,
    get_schema_generation_prompt,
    get_relevance_analysis_prompt,
    get_extraction_prompt,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        # Initialize Gemini
        if not config.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. Primary AI features will fail.")
        else:
            genai.configure(api_key=config.GEMINI_API_KEY)

        # Initialize OpenAI (Fallback)
        self.openai_client: Optional[AsyncOpenAI] = None
        if config.OPENAI_API_KEY:
            # Explicitly pass http_client=None to avoid any implicit proxy configuration issues
            # or just rely on default behavior which should work if no env vars interfere.
            # The error `TypeError: AsyncClient.__init__() got an unexpected keyword argument 'proxies'`
            # usually comes from httpx when an older version is used or arguments mismatch.
            # However, we are using AsyncOpenAI.
            # Let's try to instantiate it cleanly.
            try:
                self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
                logger.info("OpenAI fallback initialized.")
            except TypeError as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            logger.warning("OPENAI_API_KEY not set. Fallback AI features disabled.")

        # System Prompts
        self.orchestrator_instruction = ORCHESTRATOR_INSTRUCTION
        self.fast_agent_instruction = FAST_AGENT_INSTRUCTION

        self.model_name = config.DEFAULT_MODEL
        self.model = genai.GenerativeModel(self.model_name)

        self.fast_model_name = config.FAST_MODEL
        self.fast_model = genai.GenerativeModel(self.fast_model_name)

        logger.info(
            f"AI initialized. Orchestrator: {self.model_name}, Fast: {self.fast_model_name}"
        )

    async def _call_openai(
        self,
        prompt: str,
        model_type: str = "fast",
        image_bytes: Optional[bytes] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Fallback to OpenAI."""
        if not self.openai_client:
            raise Exception("OpenAI fallback not configured.")

        model = (
            config.FALLBACK_FAST_MODEL
            if model_type == "fast"
            else config.FALLBACK_DEFAULT_MODEL
        )

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        user_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]

        if image_bytes:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                }
            )

        messages.append({"role": "user", "content": user_content})

        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI fallback failed: {e}")
            raise

    def set_model(self, model_name: str):
        """Switch the active Gemini model (Orchestrator)."""
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Switched AI model to: {model_name}")

    async def analyze_seed_url(self, url: str, content: str) -> Dict[str, Any]:
        """
        Analyze the seed URL to provide a summary and suggested objectives.
        Uses the fast model.
        """
        prompt = get_seed_analysis_prompt(url, content)

        response_text = ""
        try:
            response = await self.fast_model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Gemini seed analysis failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(
                    prompt,
                    model_type="fast",
                    system_instruction=self.fast_agent_instruction,
                )
            except Exception as e2:
                logger.error(f"Fallback seed analysis failed: {e2}")
                return {
                    "summary": "Could not analyze page.",
                    "suggestions": ["Extract all text", "Extract links", "Custom..."],
                }

        try:
            cleaned_text = self._clean_json_response(response_text)
            return json.loads(cleaned_text)
        except Exception:
            return {
                "summary": "Could not analyze page.",
                "suggestions": ["Extract all text", "Extract links", "Custom..."],
            }

    async def generate_title(self, objective: str, content: str) -> str:
        """
        Generate a concise session title based on objective and content.
        Uses the fast model.
        """
        prompt = get_title_generation_prompt(objective, content)

        try:
            response = await self.fast_model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini title generation failed: {e}. Trying fallback.")
            try:
                return await self._call_openai(prompt, model_type="fast")
            except Exception as e2:
                logger.error(f"Fallback title generation failed: {e2}")
                return "Untitled Session"

    async def generate_schema(self, objective: str) -> Type[BaseModel]:
        """
        Generate a Pydantic model schema based on the user's objective.
        """
        prompt = get_schema_generation_prompt(objective)

        response_text = ""
        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Gemini schema generation failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(
                    prompt,
                    model_type="smart",
                    system_instruction=self.orchestrator_instruction,
                )
            except Exception as e2:
                logger.error(f"Fallback schema generation failed: {e2}")
                raise

        try:
            schema_json = self._clean_json_response(response_text)
            return json.loads(schema_json)
        except Exception as e:
            logger.error(f"Schema parsing failed: {e}")
            raise

    async def analyze_relevance(
        self, objective: str, content: str, url: str
    ) -> Dict[str, Any]:
        """
        Analyze if the page content is relevant to the objective and extract links.
        Uses the fast model.
        """
        prompt = get_relevance_analysis_prompt(objective, content, url)

        response_text = ""
        try:
            response = await self.fast_model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Gemini relevance analysis failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(
                    prompt,
                    model_type="fast",
                    system_instruction=self.fast_agent_instruction,
                )
            except Exception as e2:
                logger.error(f"Fallback relevance analysis failed: {e2}")
                return {"relevance_score": 0, "reason": "Error", "next_urls": []}

        try:
            cleaned_text = self._clean_json_response(response_text)
            return json.loads(cleaned_text)
        except Exception:
            return {"relevance_score": 0, "reason": "Error", "next_urls": []}

    async def analyze_api_endpoints(self, content: str, url: str) -> List[str]:
        """
        Analyze page content to find potential API endpoints.
        """
        prompt = f"""
        You are an expert web scraper. Analyze the following HTML content and identify any potential JSON API endpoints that might contain data relevant to the page's main content.
        Look for:
        - URLs in `fetch()` or `axios` calls in scripts.
        - URLs in `data-api-url` or similar attributes.
        - Links ending in `.json`.
        - URLs containing `/api/`, `/v1/`, `/graphql`.

        Return a JSON object with a single key "api_endpoints" containing a list of absolute URLs.
        If no endpoints are found, return an empty list.

        Base URL: {url}
        Content (truncated):
        {content[:50000]}
        """

        response_text = ""
        try:
            response = await self.fast_model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Gemini API analysis failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(prompt, model_type="fast")
            except Exception as e2:
                logger.error(f"Fallback API analysis failed: {e2}")
                return []

        try:
            cleaned_text = self._clean_json_response(response_text)
            result = json.loads(cleaned_text)
            return result.get("api_endpoints", [])
        except Exception:
            return []

    async def extract_data(
        self, content: str, schema: Dict[str, Any], screenshot: bytes = b""
    ) -> List[Dict[str, Any]]:
        """
        Extract structured data from content based on the schema.
        Supports multimodal input (text + image).
        """
        prompt_text = get_extraction_prompt(json.dumps(schema, indent=2), content)

        parts: List[Any] = [prompt_text]
        if screenshot:
            parts.append({"mime_type": "image/png", "data": screenshot})

        response_text = ""
        try:
            response = await self.model.generate_content_async(parts)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(
                    prompt_text,
                    model_type="smart",
                    image_bytes=screenshot if screenshot else None,
                    system_instruction=self.orchestrator_instruction,
                )
            except Exception as e2:
                logger.error(f"Fallback extraction failed: {e2}")
                return []

        try:
            cleaned_text = self._clean_json_response(response_text)
            result = json.loads(cleaned_text)
            if isinstance(result, dict):
                return [result]
            return result
        except Exception:
            return []

    async def fast_extract(self, content: str, objective: str) -> List[Dict[str, Any]]:
        """
        Fast extraction using the lightweight model.
        Extracts raw data that looks relevant to the objective.
        """
        prompt = f"""
        Objective: "{objective}"
        
        Extract ALL data from the content below that is relevant to the objective.
        Be inclusive. Capture everything that might be useful.
        Return a JSON list of objects.
        
        <content>
        {content[:30000]}
        </content>
        """

        response_text = ""
        try:
            response = await self.fast_model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Fast extraction failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(prompt, model_type="fast")
            except Exception as e2:
                logger.error(f"Fallback fast extraction failed: {e2}")
                return []

        try:
            cleaned_text = self._clean_json_response(response_text)
            result = json.loads(cleaned_text)
            if isinstance(result, dict):
                return [result]
            return result
        except Exception:
            return []

    async def refine_data(
        self, raw_data: List[Dict[str, Any]], schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Refine and validate raw data against the schema using the smart model.
        """
        if not raw_data:
            return []

        prompt = f"""
        You are a Data Quality Engineer.
        Transform the following RAW DATA into clean, valid JSON matching the SCHEMA.
        
        SCHEMA:
        {json.dumps(schema, indent=2)}
        
        RAW DATA:
        {json.dumps(raw_data, indent=2)}
        
        Rules:
        1. Fix data types (strings to numbers, etc).
        2. Remove fields not in the schema.
        3. Ensure strict adherence to the schema structure.
        4. Return a JSON list of valid objects.
        """

        response_text = ""
        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            logger.warning(f"Data refinement failed: {e}. Trying fallback.")
            try:
                response_text = await self._call_openai(
                    prompt,
                    model_type="smart",
                    system_instruction=self.orchestrator_instruction,
                )
            except Exception as e2:
                logger.error(f"Fallback data refinement failed: {e2}")
                return []

        try:
            cleaned_text = self._clean_json_response(response_text)
            result = json.loads(cleaned_text)
            if isinstance(result, dict):
                return [result]
            return result
        except Exception:
            return []

    def _clean_json_response(self, text: str) -> str:
        """Helper to clean markdown code blocks from JSON response."""
        if not text:
            return "{}"

        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # If empty after stripping
        if not text:
            return "{}"

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
        else:
            # If no JSON structure found, return empty dict string
            return "{}"

        return text
