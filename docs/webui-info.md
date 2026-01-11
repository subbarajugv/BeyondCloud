# llama.cpp WebUI Overview

## 🎨 Modern Web Interface

llama.cpp includes a **built-in modern WebUI** that comes pre-built and ready to use! The server includes it by default.

## 🚀 Quick Start

### 1. Start the Server

The WebUI is **automatically enabled** when you run `llama-server`:

```bash
# Basic usage (you'll need a model first)
./build/bin/llama-server -m /path/to/your/model.gguf -c 2048

# The server will start on http://127.0.0.1:8080
# The WebUI is accessible at the same URL
```

### 2. Disable WebUI (Optional)

If you want to run the server without the WebUI:

```bash
./build/bin/llama-server --no-webui -m /path/to/model.gguf
```

## 🛠️ Technology Stack

The WebUI is built with modern technologies:

- **Framework**: [Svelte 5](https://svelte.dev/) + [SvelteKit](https://kit.svelte.dev/)
- **Styling**: [TailwindCSS v4](https://tailwindcss.com/) + [@tailwindcss/typography](https://github.com/tailwindcss/typography)
- **UI Components**: [bits-ui](https://www.bits-ui.com/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Markdown**: [mdsvex](https://mdsvex.pngwn.io/) with math support (KaTeX)
- **Code Highlighting**: [highlight.js](https://highlightjs.org/)
- **PDF Support**: [pdfjs-dist](https://mozilla.github.io/pdf.js/)
- **Database**: [Dexie](https://dexie.org/) (IndexedDB wrapper)
- **Testing**: [Vitest](https://vitest.dev/) + [Playwright](https://playwright.dev/)

## ✨ Features

Based on the tech stack, the WebUI likely includes:

- **Chat Interface**: OpenAI-compatible chat completions
- **Multimodal Support**: Images, audio, and PDF processing
- **Markdown Rendering**: With GFM (GitHub Flavored Markdown) support
- **Math Rendering**: LaTeX/KaTeX support for mathematical expressions
- **Code Highlighting**: Syntax highlighting for code blocks
- **Dark Mode**: Using `mode-watcher`
- **Responsive Design**: TailwindCSS-based responsive UI
- **Local Storage**: IndexedDB for storing chat history and settings

## 🔧 Development

If you want to modify or develop the WebUI:

```bash
cd tools/server/webui

# Install dependencies
npm install

# Run development server with hot reload
npm run dev

# Build for production
npm run build
```

### Development Tips

- The dev server runs separately from llama-server
- You can point it to your llama-server instance by setting the base URL in browser console:
  ```js
  localStorage.setItem('base', 'http://localhost:8080')
  ```

## 📁 Pre-built Version

The pre-built WebUI is located at:
- **Compressed**: `tools/server/public/index.html.gz` (~1.1 MB)
- **Loading page**: `tools/server/public/loading.html`

The compressed version is embedded directly into the `llama-server` binary during compilation.

## 🌐 Alternative UIs

llama.cpp also includes legacy/alternative UIs:

1. **Legacy UI**: `tools/server/public_legacy/`
2. **Simple Chat**: `tools/server/public_simplechat/`
3. **Themes**: `tools/server/themes/` (buttons-top, wild)

## 📡 API Compatibility

The WebUI works with:
- **OpenAI-compatible** `/v1/chat/completions` endpoint
- **Anthropic Messages API** compatible endpoints
- Custom llama.cpp endpoints

## 🎯 Use Cases

Perfect for:
- Local LLM inference with a user-friendly interface
- Testing models before API integration
- Chat applications with multimodal support
- Educational purposes
- Privacy-focused AI applications (everything runs locally)

---

> [!TIP]
> The WebUI is production-ready and comes pre-built. You don't need to build it yourself unless you want to customize it!
