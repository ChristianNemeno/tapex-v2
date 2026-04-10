# Gemma 4 — Model Reference Documentation

> Source: Ollama Library, Google DeepMind, Unsloth Docs (April 2026)

---

## Overview

Gemma 4 is Google DeepMind's latest family of open-weight multimodal models, built from the same research as Gemini 3. Released April 2, 2026 under the **Apache 2.0 license**, it is designed for local and edge inference — phones, Raspberry Pi, laptops, and GPUs.

**Key headline:** Gemma 4 E4B (effective 4B) benchmarks competitively with models many times its size, with native document OCR, image understanding, audio input, and a 128K context window.

---

## Model Family

| Model | Architecture | Active Params | Total Params | Context | Modalities | Best For |
|---|---|---|---|---|---|---|
| **E2B** | Dense | 2.3B | 5.1B (w/ embeddings) | 128K | Text, Image, **Audio** | Phones, Raspberry Pi |
| **E4B** | Dense | 4.5B | 8B (w/ embeddings) | 128K | Text, Image, **Audio** | Phones, laptops, 6GB GPU |
| **26B A4B** | MoE (8 active / 128 total) | 3.8B active | 25.2B | 256K | Text, Image | Consumer GPUs |
| **31B** | Dense | 30.7B | 30.7B | 256K | Text, Image | Workstations |

> **"E" = Effective parameters.** E2B and E4B are architected for edge deployment — they punch well above their weight in benchmarks.

---

## Architecture Details

### E2B / E4B (Edge Models)

| Property | E2B | E4B |
|---|---|---|
| Layers | 35 | 42 |
| Sliding Window | 512 tokens | 512 tokens |
| Context Length | 128K | 128K |
| Vocabulary Size | 262K | 262K |
| Vision Encoder | ~150M params | ~150M params |
| Audio Encoder | ~300M params | ~300M params |
| Supported Modalities | Text, Image, Audio | Text, Image, Audio |

### 26B A4B (MoE)

| Property | Value |
|---|---|
| Total Parameters | 25.2B |
| Active Parameters | 3.8B |
| Layers | 30 |
| Expert Count | 8 active / 128 total + 1 shared |
| Sliding Window | 1024 tokens |
| Context Length | 256K |
| Vision Encoder | ~550M params |
| Audio | ❌ Not supported |

### Hybrid Attention Mechanism
Gemma 4 uses a **hybrid attention** design that interleaves local sliding window attention with full global attention. The final layer is always global. This enables:
- Processing speed of a lightweight model
- Long-context awareness of a larger model
- Reduced KV cache memory vs full attention

---

## Benchmark Results (Instruction-Tuned)

| Benchmark | E2B | E4B | 26B A4B | 31B |
|---|---|---|---|---|
| MMLU Pro | 60.0% | 69.4% | 82.6% | 85.2% |
| AIME 2026 | 37.5% | 42.5% | 88.3% | 89.2% |
| LiveCodeBench v6 | 44.0% | 52.0% | 77.1% | 80.0% |
| GPQA Diamond | 43.4% | 58.6% | 82.3% | 84.3% |
| MMMLU (multilingual) | 67.4% | 76.6% | 86.3% | 88.4% |
| **MMMU Pro (Vision)** | 44.2% | **52.6%** | 73.8% | 76.9% |
| **OmniDocBench 1.5** ↓ | 0.290 | **0.181** | 0.149 | 0.131 |
| **MATH-Vision** | 52.4% | **59.5%** | 82.4% | 85.6% |

> OmniDocBench = document parsing accuracy (lower edit distance = better). E4B at 0.181 is strong for a 4B-class model.

---

## Vision Capabilities

Gemma 4 has native vision understanding relevant to document/MCQ extraction:

- ✅ **OCR** — including multilingual text recognition
- ✅ **Document / PDF parsing** — via OmniDocBench training
- ✅ **Handwriting recognition**
- ✅ **Chart and diagram comprehension**
- ✅ **Screen and UI understanding**
- ✅ **Variable aspect ratio and resolution support**
- ✅ **Interleaved multimodal input** — freely mix text and images in any order

### Variable Image Resolution (Token Budget)

Gemma 4 uses a **configurable visual token budget** to trade quality for speed:

| Token Budget | Use Case |
|---|---|
| 70 | Fast classification, video frame processing |
| 140 | Quick captioning |
| 280 | General image understanding |
| 560 | Detailed document reading |
| **1120** | **OCR, small text, dense documents** ← use this for MCQ |

> **For MCQ extraction from images/PDFs: use token budget 1120** to preserve fine-grained text detail.

---

## Running with Ollama

### Install & Pull

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull edge models
ollama pull gemma4:e2b   # 7.2GB download
ollama pull gemma4:e4b   # 9.6GB download  ← recommended for RTX 3050 6GB

# Pull workstation models
ollama pull gemma4:26b   # 18GB — tight on 6GB VRAM
ollama pull gemma4:31b   # 20GB — requires 24GB+
```

### Run Chat

```bash
ollama run gemma4:e4b
```

### REST API (OpenAI-Compatible)

Ollama exposes an OpenAI-compatible endpoint at `http://localhost:11434`.

```bash
curl http://localhost:11434/api/chat \
  -d '{
    "model": "gemma4:e4b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Python SDK

```python
from ollama import chat

response = chat(
    model='gemma4:e4b',
    messages=[{'role': 'user', 'content': 'Extract MCQs from this image.'}],
)
print(response.message.content)
```

### Python with Image Input

```python
from ollama import chat

with open("page.png", "rb") as f:
    image_bytes = f.read()

response = chat(
    model='gemma4:e4b',
    messages=[
        {
            'role': 'user',
            'content': 'Extract all MCQs from this image as JSON.',
            'images': [image_bytes],   # pass image BEFORE text for best performance
        }
    ],
)
```

> **Modality order tip:** Always place image/audio content **before** text in your prompt for optimal performance.

---

## Best Practices

### 1. Sampling Parameters

Always use these settings for consistent quality:

```python
options = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
}
```

### 2. Thinking Mode

Gemma 4 supports a built-in reasoning/thinking mode.

```python
# Enable thinking — add <|think|> at the START of system prompt
system_prompt = "<|think|>\nYou are an MCQ extractor..."

# Disable thinking — omit the token
system_prompt = "You are an MCQ extractor..."
```

When thinking is enabled, the model outputs:
```
<|channel>thought
[Internal reasoning steps]
<channel|>
[Final answer]
```

> Strip the `<|channel>thought ... <channel|>` block when parsing output if you only need the final answer.

### 3. Multi-Turn Conversations

Do **not** include thinking content in conversation history. Only pass the final answer to the next turn:

```python
# ✅ Correct
history = [
    {"role": "user", "content": "Extract MCQs"},
    {"role": "assistant", "content": "[final answer only, no thought block]"},
]

# ❌ Wrong
history = [
    {"role": "user", "content": "Extract MCQs"},
    {"role": "assistant", "content": "<|channel>thought\n...<channel|>[answer]"},  # BAD
]
```

### 4. System Prompt (Native Support)

Gemma 4 adds native `system` role support (unlike Gemma 3):

```python
messages = [
    {
        "role": "system",
        "content": "You are an MCQ extraction engine. Always respond in valid JSON."
    },
    {
        "role": "user",
        "content": "Extract all MCQs from the attached image."
    }
]
```

---

## Hardware Requirements (VRAM / RAM)

| Model | Q4 (4-bit) | Q8 (8-bit) | BF16 (full) |
|---|---|---|---|
| E2B | ~3GB | ~5GB | ~10GB |
| E4B | ~5GB | ~8GB | ~16GB |
| 26B A4B | ~18GB | — | ~50GB |
| 31B | ~20GB | ~34GB | ~62GB |

> For RTX 3050 6GB: **E4B at Q4** fits at ~5GB with ~1GB headroom.

---

## Ollama Commands Quick Reference

```bash
ollama list                    # list downloaded models
ollama run gemma4:e4b          # interactive chat
ollama rm gemma4:e2b           # remove model
ollama show gemma4:e4b         # show model info
ollama ps                      # show running models
```

---

## Changelog vs Gemma 3

| Feature | Gemma 3 | Gemma 4 |
|---|---|---|
| Max context (small) | 128K | 128K |
| Max context (large) | 128K | **256K** |
| Audio input | ❌ | ✅ (E2B, E4B) |
| Native system role | ❌ | ✅ |
| Thinking mode | ❌ | ✅ |
| Document OCR bench | 0.365 (27B) | **0.181 (E4B)** |
| License | Apache 2.0 | Apache 2.0 |
| MoE architecture | ❌ | ✅ (26B A4B) |
