# DevMatrix UI - React Frontend

Modern chat-based UI for DevMatrix with real-time WebSocket communication and multi-agent orchestration.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast development and building
- **Tailwind CSS** - Utility-first styling
- **Socket.IO** - Real-time WebSocket communication
- **TanStack Query** - Data fetching and caching
- **Zustand** - State management
- **Monaco Editor** - Code editor (planned)
- **React Markdown** - Markdown rendering with syntax highlighting

## Development

### Local Development (Standalone)

```bash
cd src/ui
npm install
npm run dev
```

The UI will be available at http://localhost:3000 with API proxy to http://localhost:8000

### Docker Development

```bash
# Start UI dev server with hot reload
docker compose --profile dev up ui

# Or start everything
docker compose --profile dev up
```

### Building for Production

```bash
cd src/ui
npm run build
```

Builds to `../api/static/` directory to be served by FastAPI.

## Features

### Phase 1: Chat Foundation ✅

- **Real-time Chat**: WebSocket-based bidirectional communication
- **Agent Integration**: Direct connection to OrchestratorAgent
- **Command System**: Special commands like `/orchestrate`, `/help`, `/analyze`
- **Markdown Support**: Full GFM markdown with syntax highlighting
- **Conversation History**: Persistent chat sessions
- **Auto-complete**: Command suggestions with keyboard navigation
- **Connection Status**: Real-time connection indicator
- **Responsive Design**: Mobile-first approach

### Phase 2: Editor Integration (Planned)

- Monaco Editor embedded
- File tree navigation
- Diff viewer for agent changes
- Live code preview

### Phase 3: Real-time Executions (Planned)

- Execution monitoring dashboard
- Progress tracking per task
- Live logs streaming
- DAG visualization

## Project Structure

```
src/ui/
├── src/
│   ├── components/
│   │   ├── chat/           # Chat UI components
│   │   ├── editor/         # Code editor (planned)
│   │   └── shared/         # Shared components
│   ├── hooks/              # React hooks
│   │   ├── useChat.ts      # Chat functionality
│   │   └── useWebSocket.ts # WebSocket connection
│   ├── stores/             # Zustand stores
│   │   └── chatStore.ts    # Chat state management
│   ├── services/           # API and WebSocket services
│   │   ├── api.ts          # REST API client
│   │   └── websocket.ts    # WebSocket service
│   ├── App.tsx             # Main application
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Available Commands

### Chat Commands

- `/help` - Show available commands
- `/orchestrate <description>` - Start multi-agent workflow
- `/analyze <target>` - Analyze code or project
- `/test` - Run tests
- `/clear` - Clear conversation history
- `/workspace` - Show current workspace info

## Configuration

### Environment Variables

```bash
# API endpoint (default: http://localhost:8000)
VITE_API_URL=http://localhost:8000

# WebSocket endpoint (default: same as API)
VITE_WS_URL=http://localhost:8000
```

### Vite Proxy Configuration

The dev server proxies API and WebSocket requests:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/socket.io': {
      target: 'http://localhost:8000',
      ws: true,
    },
  },
}
```

## WebSocket Events

### Client → Server

- `join_chat` - Join chat room
- `send_message` - Send chat message
- `leave_chat` - Leave chat room
- `get_file_tree` - Get workspace file tree
- `read_file` - Read file content
- `write_file` - Write file content
- `join_execution` - Monitor execution
- `leave_execution` - Stop monitoring execution

### Server → Client

- `connected` - Connection established
- `chat_joined` - Successfully joined chat
- `message` - New message or response chunk
- `error` - Error occurred
- `file_tree` - File tree data
- `file_content` - File content
- `execution_update` - Execution progress update

## Development Tips

### Hot Reload

Both frontend and backend support hot reload in development:

- **Frontend**: Vite HMR for instant updates
- **Backend**: Uvicorn `--reload` for API changes

### Debugging WebSocket

Open browser console to see WebSocket events:

```javascript
// In browser console
wsService.on('message', console.log)
wsService.on('error', console.error)
```

### Component Development

Use React DevTools for debugging:

```bash
# Install React DevTools browser extension
# Available for Chrome, Firefox, Edge
```

## Testing (Planned)

```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

## Build Optimization

Production builds are optimized:

- **Code splitting**: Dynamic imports for routes
- **Tree shaking**: Remove unused code
- **Minification**: Terser for JS, cssnano for CSS
- **Compression**: Brotli and gzip
- **Asset optimization**: Image compression, font subsetting

## Troubleshooting

### WebSocket Connection Issues

```bash
# Check if Socket.IO server is running
curl http://localhost:8000/socket.io/
```

### Build Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Type Errors

```bash
# Regenerate TypeScript declarations
npm run build -- --force
```

## Contributing

1. Follow TypeScript best practices
2. Use functional components with hooks
3. Implement proper error boundaries
4. Add proper accessibility attributes
5. Write meaningful commit messages
6. Keep components focused and reusable

## License

MIT
