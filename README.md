# HPU — Native AI Integration Test

A separate Streamlit test application for connecting HPU directly to OpenAI or Anthropic through their official APIs.

## Files
- `app.py` — Streamlit interface and provider calls
- `hpu_core.py` — HPU request preparation, basic evaluation and cost calculation
- `requirements.txt` — Python dependencies
- `hpu_integration_test.db` — created automatically when the app runs

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud
1. Create a NEW GitHub repository, for example `hpu-integration-test`.
2. Upload `app.py`, `hpu_core.py`, and `requirements.txt`.
3. In Streamlit Community Cloud, create a new app from that repository and select `app.py`.
4. Open the app. Select a provider and enter its API key in the sidebar.

## API keys and billing
- OpenAI API keys: https://platform.openai.com/api-keys
- OpenAI API pricing: https://openai.com/api/pricing/
- Anthropic Console: https://console.anthropic.com/
- ChatGPT and Claude subscriptions are separate from API billing.
- Never paste an API key into a public GitHub file, source code, screenshot, or chat message.

## Cost tracking
The app records provider-reported input and output tokens for successful text API calls. Enter the current per-million-token input and output rates for the selected model in the sidebar. The app calculates an estimate and stores the rates used with each operation.

This is a test-level estimate, not an official invoice. It does not currently include image/audio charges, cached-token pricing, web-search charges, taxes, or other provider-specific billable units. Check the provider's current pricing and usage dashboard.

## Important limitations
- The basic HPU response check only checks that a response exists and contains at least three words. It does not verify truth, evidence, quality, or suitability.
- The app is a test environment, not a production multi-user service.
- API keys are kept in Streamlit session state for this test. For production, implement secure server-side secret storage, user authentication, access controls, rate limits, audit logs, and provider-specific credential management.
- The SQLite database is local to the app runtime. On Streamlit Community Cloud, local files may not be durable across app rebuilds/redeployments. Use managed persistent storage for production.
