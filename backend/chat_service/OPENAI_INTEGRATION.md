# OpenAI Integration in Chat Service

## Overview

The Chat Service now includes advanced OpenAI integration for enhanced natural language understanding and intelligent query processing. This integration provides:

- **Smart Intent Detection**: Uses OpenAI's language models to understand complex user queries
- **Context-Aware Responses**: Generates intelligent, contextual responses based on user questions
- **Cost Analysis**: Calculates energy costs and provides financial insights
- **Efficiency Insights**: Offers recommendations for energy optimization
- **Fallback System**: Maintains rule-based processing when OpenAI is unavailable

## Features

### 🧠 Enhanced Intent Detection
- **OpenAI-Powered**: Uses GPT models for natural language understanding
- **Rule-Based Fallback**: Falls back to deterministic logic when needed
- **Confidence Scoring**: Provides confidence levels for intent detection
- **Context Awareness**: Understands complex, multi-part questions

### 💰 Cost Analysis
- **Energy Cost Calculation**: Estimates electricity costs based on consumption
- **Time-Based Analysis**: Provides cost breakdowns by hour, day, week, month
- **Device-Specific Costs**: Calculates costs for individual devices
- **Efficiency Ratings**: Compares device efficiency and cost-effectiveness

### 🔍 Energy Insights
- **Consumption Patterns**: Identifies usage trends and patterns
- **Peak Usage Detection**: Finds high-consumption periods
- **Device Comparison**: Ranks devices by energy efficiency
- **Optimization Tips**: Provides actionable recommendations

## Configuration

### Environment Variables

```bash
# Enable/disable OpenAI integration
ENABLE_OPENAI=true

# Your OpenAI API key
OPENAI_API_KEY=your_openai_api_key_here

# OpenAI model to use
OPENAI_MODEL=gpt-3.5-turbo

# NLP processing parameters
MAX_TOKENS=500
TEMPERATURE=0.1
CONFIDENCE_THRESHOLD=0.7
```

### Setup Instructions

1. **Get OpenAI API Key**:
   - Visit [OpenAI Platform](https://platform.openai.com/)
   - Create an account and get your API key
   - Add it to your environment variables

2. **Configure Environment**:
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## API Endpoints

### OpenAI Status
```http
GET /openai/status
```
Returns the current status of OpenAI integration and connection test results.

**Response Example**:
```json
{
  "status": "connected",
  "message": "OpenAI integration is working",
  "model": "gpt-3.5-turbo",
  "test_response": "Hello! How can I help you today?",
  "capabilities": [
    "Enhanced intent detection",
    "Natural language understanding",
    "Context-aware responses",
    "Smart query interpretation"
  ]
}
```

### Sample Queries
```http
GET /openai/sample-queries
```
Returns sample queries to test the OpenAI integration.

**Response Example**:
```json
{
  "sample_queries": [
    "How much energy did my AC use last week?",
    "What's my highest-consuming device today?",
    "Compare energy usage of my devices this month",
    "Give me an energy analysis for this week",
    "What's my energy cost for today?"
  ],
  "testing_tips": [
    "Use /openai/status to check connection",
    "Use /openai/test with POST method and query parameter",
    "Test with natural language questions",
    "Check both OpenAI and rule-based fallback"
  ]
}
```

### Test OpenAI Intent Detection
```http
POST /openai/test
Content-Type: application/json

{
  "test_query": "How much energy did my AC use last week?"
}
```
Tests OpenAI intent detection with a specific query.

**Response Example**:
```json
{
  "query": "How much energy did my AC use last week?",
  "intent_detection": {
    "intent": "device_energy",
    "device": "AC",
    "time_period": "week",
    "confidence": 0.95,
    "extracted_info": {
      "device_name": "AC",
      "time_range": "last week",
      "query_type": "energy_consumption"
    }
  },
  "success": true
}
```

## Query Processing

### Intent Types

1. **Device Energy** (`device_energy`)
   - Queries about specific device consumption
   - Example: "How much energy did my AC use last week?"

2. **Device Comparison** (`device_comparison`)
   - Compares energy usage across devices
   - Example: "Which devices use the most power?"

3. **Total Consumption** (`total_consumption`)
   - Overall energy consumption summaries
   - Example: "What's my total energy usage this month?"

4. **Energy Analysis** (`energy_analysis`)
   - Detailed analysis and insights
   - Example: "Analyze my energy consumption patterns"

5. **Cost Analysis** (`cost_analysis`)
   - Cost calculations and estimates
   - Example: "What's my energy cost for this week?"

### Processing Flow

```
User Query → OpenAI Intent Detection → Query Processing → Response Generation
     ↓              ↓                      ↓                ↓
Natural Language → Structured Intent → Data Retrieval → Formatted Response
     ↓              ↓                      ↓                ↓
Fallback to      Confidence Score    Cost Analysis    Charts & Insights
Rule-Based       Intent Validation   Efficiency Calc   Recommendations
```

## Testing

### Test Script
Use the provided test script to verify OpenAI integration:

```bash
cd backend/chat_service
python test_openai.py
```

### Manual Testing
1. **Check Status**: `GET /openai/status`
2. **Get Samples**: `GET /openai/sample-queries`
3. **Test Intent**: `POST /openai/test` with sample queries
4. **Verify Fallback**: Test with OpenAI disabled

### Test Queries
- "How much energy did my AC use last week?"
- "What's my highest-consuming device today?"
- "Compare energy usage of my devices this month"
- "Give me an energy analysis for this week"
- "What's my energy cost for today?"

## Error Handling

### OpenAI Unavailable
- Automatically falls back to rule-based processing
- Maintains service availability
- Logs fallback events for monitoring

### API Errors
- Graceful error handling
- User-friendly error messages
- Detailed logging for debugging

### Rate Limiting
- Respects OpenAI API rate limits
- Implements exponential backoff
- Queue management for high-traffic scenarios

## Performance

### Response Times
- **OpenAI Processing**: 1-3 seconds (depending on query complexity)
- **Rule-Based Fallback**: <100ms
- **Cache Hit**: <50ms

### Optimization
- **Connection Pooling**: Reuses OpenAI client connections
- **Response Caching**: Caches common query responses
- **Async Processing**: Non-blocking query handling

## Security

### API Key Protection
- Environment variable storage
- No hardcoded keys in source code
- Secure key rotation support

### Input Validation
- Query length limits (500 characters)
- Content filtering and sanitization
- Rate limiting per user

### Data Privacy
- No user data sent to OpenAI (only queries)
- Local processing of sensitive information
- Audit logging for compliance

## Monitoring

### Health Checks
- OpenAI connection status
- API response times
- Error rates and types
- Fallback usage statistics

### Metrics
- Query processing times
- Intent detection accuracy
- Cost calculation precision
- User satisfaction scores

## Troubleshooting

### Common Issues

1. **OpenAI Connection Failed**
   - Check API key validity
   - Verify network connectivity
   - Check OpenAI service status

2. **High Response Times**
   - Monitor OpenAI API performance
   - Check rate limiting
   - Review query complexity

3. **Intent Detection Errors**
   - Validate query format
   - Check confidence thresholds
   - Review fallback logic

### Debug Mode
Enable debug logging for detailed troubleshooting:

```bash
LOG_LEVEL=debug
```

## Future Enhancements

### Planned Features
- **Multi-Model Support**: Choose between different OpenAI models
- **Custom Training**: Fine-tune models for energy domain
- **Voice Integration**: Speech-to-text and text-to-speech
- **Predictive Analytics**: Energy usage forecasting
- **Smart Recommendations**: AI-powered optimization suggestions

### Integration Opportunities
- **Weather Data**: Correlate energy usage with weather
- **Smart Home APIs**: Direct device control integration
- **Utility APIs**: Real-time pricing and billing
- **Social Features**: Community energy challenges

## Support

### Documentation
- API Reference: `/docs` (Swagger UI)
- OpenAPI Spec: `/openapi.json`
- Health Check: `/health`

### Logs
- Application logs: `logs/chat_service.log`
- OpenAI API logs: `logs/openai.log`
- Error logs: `logs/errors.log`

### Contact
For issues or questions about OpenAI integration:
- Check the logs for error details
- Review the configuration
- Test with the provided test script
- Consult the API documentation
