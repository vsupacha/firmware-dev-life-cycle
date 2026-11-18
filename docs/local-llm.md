# Local LLM setup for the requirement prototype

Verified model tags and source pages on **2026-10-31**. The actual office machine and its GPU have not been benchmarked in this work.

## Options for RTX 4060 8GB

| Option | Exact Ollama tag | Observed download package | Suggested use |
| --- | --- | --- | --- |
| Gemma 4 E4B | `gemma4:e4b` | About 6.6 GB; tag page lists Q4_K_M model weights plus other components | Requested first experiment; use text input and short context, then measure actual VRAM/offload. |
| Gemma 4 E2B | `gemma4:e2b` | About 4.6 GB; tag page lists Q4_K_M model weights plus other components | Smaller fallback when E4B is slow or memory-constrained. |
| Other installed local model | Enter the exact server model ID | Depends on model/quantization | Compare requirement quality using the same stories and questions. |

Sources: [Ollama E4B](https://ollama.com/library/gemma4:e4b), [Ollama E2B](https://ollama.com/library/gemma4:e2b), [Google Gemma 4 model overview](https://ai.google.dev/gemma/docs/core).

Download size is not total runtime VRAM. KV cache, context, runtime overhead and other GPU applications affect fit; partial CPU offload can affect speed. The E designation refers to effective parameters, not a simple total-resident-weight count. Do not assume E4B fits entirely on an 8GB GPU from its name alone.

## Ollama

Install a compatible current Ollama separately on office, then choose the model to download. The prototype never installs Ollama or pulls models automatically.

```powershell
ollama pull gemma4:e4b
ollama list
```

For the smaller fallback, use `ollama pull gemma4:e2b`. If the service is not already running, start it with `ollama serve`. The default UI endpoint is `http://127.0.0.1:11434` and uses `/api/tags` for discovery and `/api/chat` for chat. See [the official chat API](https://docs.ollama.com/api/chat).

Select Ollama in the sidebar and use Show installed models to check connectivity. Presets fill the exact tag; the model-name field stays editable. Start with context 4096, max output 1024, temperature 0.2, thinking disabled and JSON mode enabled. Context 2048 is available for smaller prompts but may be too small for the schema and selected-story context. The app will reject an estimated over-budget request instead of silently truncating that story.

If a particular runtime rejects JSON mode, disable it and use the same JSON-output prompt. Malformed/truncated responses are not applied. A timeout leaves the user's message saved but applies no model proposal; shorten the request, adjust output/context or try E2B.

On office, inspect `ollama ps` and `nvidia-smi` while generating, and record model/tag, runtime version, context, output length, GPU/CPU loading, observed latency and requirement quality. These are experiment results, separate from provider firmware capabilities.

## OpenAI-compatible local server

Select OpenAI-compatible and enter the local server base URL, for example `http://127.0.0.1:1234/v1`, plus its actual loaded model ID. This adapter uses `/v1/models` and `/v1/chat/completions`; compatibility is a server prerequisite, not an assertion that every runtime supports identical options.

Context allocation for this mode is controlled by the local server, not the Ollama context slider. The app sends max output tokens and optional JSON response format. Disable JSON mode if the server does not support it. An optional API key is kept only in the current session and sent to the endpoint entered by the user.

The app performs direct HTTP calls to the chosen endpoint with bounded timeouts, bypassing environment proxies. It does not contact a cloud LLM by default. Verify the endpoint before sending engineering input.

## Repeatable comparison

Use the same imported capability snapshot and initial user request for E4B and E2B. Evaluate whether the agent preserves intent, asks useful questions, avoids inventing hardware facts, produces usable criteria/test intent and returns valid structured proposals. A valid JSON response alone is not evidence of a good requirement.
