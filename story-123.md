# Grok AI Integration

This document provides details on how to securely configure and use the Grok AI integration in the Finance Service Agent.

## Security Configuration

1. Obtain a Grok AI API key from the Grok AI platform
2. Copy the `.env.example` file to `.env` (if not already done)
3. Add your Grok AI API key to the `.env` file:
   ```
   GROK_API_KEY=your_grok_ai_api_key_here
   ```
4. Generate a secure random API key to protect the endpoints:
   ```
   API_KEY=your_secure_random_key_here
   ```
   
   For production, use a high-entropy random key generated with a secure method. For example:
   ```python
   import secrets
   secrets.token_urlsafe(32)
   ```

## Available Endpoints

### `/ask-grok`

This endpoint uses Grok AI to answer financial and investment-related questions. It combines Grok AI with specialized financial tools and web search capabilities.

**Method**: GET  
**Parameters**:
- `query`: The financial question to ask (required)

**Headers**:
- `X-API-Key`: Your API key for authentication (required if API_KEY is set in .env)
- `Accept`: Set to "text/html" to receive HTML response, otherwise JSON is returned

**Example Request**:
```
GET /ask-grok?query=What are the best dividend stocks to invest in right now?
X-API-Key: your_api_key_here
```

**Example Response**:
```json
{
  "question": "What are the best dividend stocks to invest in right now?",
  "answer": "Based on current market analysis, some of the best dividend stocks to consider include... [detailed answer with current market insights]"
}
```

## Authentication & Security

All endpoints are protected with API key authentication if `API_KEY` is set in the environment:

1. Set a secure, random API key in the `.env` file
2. Include this key in all requests using the `X-API-Key` header
3. If `API_KEY` is not set, authentication is disabled (not recommended for production)

Input validation and sanitization are applied to all user inputs to prevent injection attacks.

## Comparison with Meta-LLaMA

The Grok AI integration serves as an alternative to the existing Meta-LLaMA model in our system. Here are the key differences:

1. **Advanced Reasoning**: Grok AI provides different reasoning capabilities compared to Meta-LLaMA
2. **Real-time Data**: Both implementations leverage the same tools for accessing financial data and web search
3. **Response Style**: Users may notice differences in how responses are formatted and reasoned

## Error Handling

If you encounter issues with the Grok AI integration, please check:

1. That your API key is correctly configured in the `.env` file
2. That you are sending a valid query parameter
3. That you are including the correct authentication header
4. The API logs for any specific error messages

## Security Considerations

- The Grok AI API key and endpoint API keys should be kept secure and never exposed in client-side code
- All requests are processed server-side to maintain API key security
- User queries are sanitized and validated before processing
- HTTPS is enforced for all API communication with Grok AI
- Regular security updates and vulnerability assessments should be performed