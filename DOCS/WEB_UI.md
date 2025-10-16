# DevMatrix Web UI

**Estado**: ✅ Funcional
**Última actualización**: 2025-10-14
**Tecnologías**: React 18, TypeScript, Vite, Tailwind CSS, Socket.IO Client

## Descripción General

Interfaz web conversacional para interactuar con el sistema DevMatrix mediante chat en tiempo real. Permite a los usuarios describir proyectos y recibir orquestación multi-agente automática.

## Arquitectura

```
src/ui/
├── src/
│   ├── components/
│   │   └── chat/
│   │       ├── ChatWindow.tsx      # Componente principal del chat
│   │       ├── ChatInput.tsx       # Input con autocompletado de comandos
│   │       └── MessageList.tsx     # Lista de mensajes con markdown
│   ├── hooks/
│   │   ├── useChat.ts             # Hook para gestión de mensajes
│   │   └── useWebSocket.ts        # Hook para conexión WebSocket
│   ├── services/
│   │   └── websocket.ts           # Servicio singleton de WebSocket
│   ├── App.tsx                    # Componente raíz
│   └── main.tsx                   # Entry point
├── vite.config.ts                 # Configuración de Vite
└── package.json
```

## Componentes Principales

### ChatWindow
**Ubicación**: `src/components/chat/ChatWindow.tsx`

Componente principal que orquesta toda la experiencia del chat:

**Features**:
- ✅ Auto-scroll a nuevos mensajes
- ✅ Auto-focus en input después de respuestas
- ✅ Botón "Nuevo Proyecto" para reiniciar conversación
- ✅ Indicador de estado de conexión (Connected/Disconnected)
- ✅ Indicador de carga mientras el agente procesa
- ✅ Soporta minimizar/cerrar

**Props**:
```typescript
interface ChatWindowProps {
  workspaceId?: string           // ID del workspace (opcional)
  onClose?: () => void           // Callback para cerrar
  isMinimized?: boolean          // Estado minimizado
  onToggleMinimize?: () => void  // Toggle minimize
}
```

### ChatInput
**Ubicación**: `src/components/chat/ChatInput.tsx`

Input inteligente con soporte para comandos:

**Features**:
- ✅ Auto-resize dinámico del textarea
- ✅ Autocompletado de comandos (/, /help, /orchestrate, etc.)
- ✅ Navegación con flechas en sugerencias
- ✅ Submit con Enter (Shift+Enter para nueva línea)
- ✅ Deshabilitado durante carga
- ✅ Exposed focus() method via forwardRef

**Comandos disponibles**:
- `/help` - Mostrar ayuda
- `/orchestrate <descripción>` - Orquestar proyecto
- `/analyze` - Analizar código
- `/test` - Ejecutar tests
- `/clear` - Limpiar historial
- `/workspace` - Info del workspace

### MessageList
**Ubicación**: `src/components/chat/MessageList.tsx`

Renderiza mensajes con soporte para markdown:

**Features**:
- ✅ Markdown rendering (react-markdown + remark-gfm + rehype-highlight)
- ✅ Syntax highlighting para bloques de código
- ✅ Diferenciación visual usuario/asistente/sistema
- ✅ Timestamps en formato HH:mm
- ✅ Indicador de carga con animación
- ✅ Modo oscuro con contraste adecuado

**Tipos de mensajes**:
- `user` - Mensajes del usuario (azul, alineado a la derecha)
- `assistant` - Respuestas del agente (gris, con markdown)
- `system` - Mensajes del sistema (amarillo, con borde)

## Hooks Personalizados

### useChat
**Ubicación**: `src/hooks/useChat.ts`

Hook principal para gestión del chat:

```typescript
const {
  conversationId,    // ID de la conversación actual
  messages,          // Array de mensajes
  isLoading,         // Estado de carga
  isConnected,       // Estado de conexión WebSocket
  sendMessage,       // Función para enviar mensajes
  clearMessages,     // Función para limpiar historial
} = useChat({ workspaceId })
```

**Funcionalidad**:
- Gestiona ciclo de vida de la conversación
- Registra event listeners de WebSocket
- Maneja estados de carga
- Auto-join a chat room al conectar
- Procesa diferentes tipos de mensajes (user, assistant, status, error)

**Bug fix crítico** (2025-10-14):
- Separados los useEffects para listeners y join
- Listeners ahora persisten durante toda la sesión
- Evita limpieza prematura de event handlers

### useWebSocket
**Ubicación**: `src/hooks/useWebSocket.ts`

Hook para gestión de conexión WebSocket:

```typescript
const {
  isConnected,  // Estado de conexión
  send,         // Enviar evento
  on,           // Registrar listener
} = useWebSocket(url)
```

## Servicios

### WebSocketService
**Ubicación**: `src/services/websocket.ts`

Singleton que maneja la conexión Socket.IO:

**Métodos**:
- `connect(url)` - Conectar al servidor
- `disconnect()` - Desconectar
- `send(event, data)` - Emitir evento al servidor
- `on(event, callback)` - Registrar listener
- `emit(event, data)` - Emitir evento localmente (interno)

**Eventos del servidor**:
- `connected` - Conexión establecida
- `chat_joined` - Usuario unido al chat
- `message` - Mensaje recibido (user_message, assistant, status, error)
- `error` - Error del servidor

## Flujo de Mensajes

### 1. Conexión Inicial
```
1. Usuario abre la app
2. WebSocket se conecta a ws://localhost:8000/socket.io
3. Servidor emite 'connected' con session ID
4. Cliente emite 'join_chat' con workspace_id (opcional)
5. Servidor emite 'chat_joined' con conversation_id
```

### 2. Envío de Mensaje
```
1. Usuario escribe en ChatInput y presiona Enter
2. ChatInput llama sendMessage(content)
3. useChat emite 'send_message' via WebSocket
4. Servidor procesa y emite 'message' con type='user_message'
5. Cliente agrega mensaje a la lista
6. Servidor procesa con LLM y emite respuesta(s)
7. Cliente recibe 'message' con type='message' (assistant)
8. Mensaje se renderiza con markdown
9. Auto-scroll y auto-focus
```

### 3. Tipos de Respuesta

**Conversacional** (saludos, preguntas):
```json
{
  "type": "message",
  "role": "assistant",
  "content": "¡Hola! ¿En qué te puedo ayudar?",
  "done": true
}
```

**Orquestación** (implementación):
```json
{
  "type": "status",
  "content": "Starting orchestration...",
  "done": false
}
```
Seguido de:
```json
{
  "type": "message",
  "role": "assistant",
  "content": "## Orchestration Complete\n\n**Workspace**: `xxx`...",
  "metadata": { "workspace_id": "...", "tasks": [...] },
  "done": true
}
```

## Estilos y Temas

### Tailwind CSS
Utiliza Tailwind con soporte para modo oscuro:

**Colores principales**:
- Primary: `primary-{50-900}` (azul)
- Gray: `gray-{50-900}` (grises neutros)
- Estados: `green-`, `yellow-`, `red-`

**Modo oscuro**:
```css
.dark\:bg-gray-900  /* Fondo oscuro */
.dark\:text-gray-100 /* Texto claro en modo oscuro */
```

### Contraste de Texto
**Fix aplicado** (2025-10-14):
- Input: `text-gray-900 dark:text-gray-100`
- Mensajes assistant: `text-gray-900 dark:text-gray-100`
- Mensajes system: `text-yellow-900 dark:text-yellow-100`

## Build y Deploy

### Desarrollo
```bash
cd src/ui
npm install
npm run dev  # Servidor de desarrollo en http://localhost:5173
```

### Producción
```bash
cd src/ui
npm run build  # Build en ../api/static/
```

Los assets se generan en `src/api/static/` para ser servidos por FastAPI:
```
src/api/static/
├── index.html
└── assets/
    ├── index-[hash].js
    └── index-[hash].css
```

### Configuración de Vite
```typescript
// vite.config.ts
export default defineConfig({
  base: '/',
  build: {
    outDir: '../api/static',  // Output a carpeta del API
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',      // Proxy API
      '/socket.io': {                       // Proxy WebSocket
        target: 'http://localhost:8000',
        ws: true,
      },
    },
  },
})
```

## Testing

### Tests Manuales

**Checklist de funcionalidad**:
- [ ] Conexión WebSocket exitosa
- [ ] Envío y recepción de mensajes
- [ ] Renderizado de markdown
- [ ] Syntax highlighting de código
- [ ] Auto-scroll a nuevos mensajes
- [ ] Auto-focus después de respuestas
- [ ] Botón "Nuevo Proyecto" funciona
- [ ] Comandos (/) autocomplete
- [ ] Modo oscuro/claro
- [ ] Contraste de texto adecuado
- [ ] Responsive design

### Tests de Integración

**Flujos a validar**:
1. **Saludo simple**: "Hola" → Respuesta conversacional
2. **Diseño con preguntas**: "diseñar una app" → Preguntas de clarificación
3. **Implementación directa**: "crear API REST con FastAPI" → Orquestación inmediata
4. **Comandos**: "/help" → Lista de comandos

## Mejoras Implementadas (2025-10-14)

### UI/UX
✅ Contraste de texto mejorado (negro/blanco sobre fondos)
✅ Auto-focus en input después de cada respuesta
✅ Botón "Nuevo Proyecto" para reiniciar conversación
✅ Mejor feedback visual de estados (loading, connected)

### Chat Logic
✅ Detección inteligente de intención (conversacional vs orquestación)
✅ Menos preguntas repetitivas del agente
✅ Transición suave entre modos
✅ Soporte para mensajes largos con detalles técnicos

### Bug Fixes
✅ **CRÍTICO**: Event listeners no se limpiaban correctamente
✅ WebSocket messages ahora llegan correctamente a useChat
✅ Separación de concerns entre listener registration y chat joining

## Problemas Conocidos

### Limitaciones Actuales
⚠️ No hay historial persistente (se pierde al recargar)
⚠️ No se pueden editar mensajes enviados
⚠️ No hay búsqueda en conversación
⚠️ No se puede exportar conversación
⚠️ Sin soporte para attachments/archivos

### Próximas Mejoras Sugeridas
- [ ] Persistencia de conversaciones en backend
- [ ] Historial de conversaciones con búsqueda
- [ ] Export de conversación (Markdown, JSON)
- [ ] Copiar respuestas individuales
- [ ] Attachments para código/archivos
- [ ] Streaming de respuestas token por token
- [ ] Reacciones/feedback a respuestas
- [ ] Modo split-screen (chat + código)

## Configuración

### Variables de Entorno
No requiere variables de entorno específicas para el frontend.

### API Endpoint
El frontend se conecta a:
- HTTP API: `http://localhost:8000/api`
- WebSocket: `ws://localhost:8000/socket.io`

En producción estos URLs se configuran automáticamente.

## Troubleshooting

### WebSocket no conecta
1. Verificar que el API esté corriendo: `docker compose ps`
2. Verificar logs del API: `docker compose logs -f api`
3. Verificar que el puerto 8000 esté abierto

### Mensajes no aparecen
1. Abrir DevTools → Console
2. Buscar logs `[WebSocketService]` y `[useChat]`
3. Verificar que los listeners estén registrados
4. Verificar que los eventos lleguen del backend

### Texto invisible
1. Verificar que los estilos tengan `text-gray-900 dark:text-gray-100`
2. Limpiar caché del navegador
3. Reconstruir con `npm run build`

### Build falla
1. Limpiar node_modules: `rm -rf node_modules && npm install`
2. Verificar versión de Node: `node --version` (debe ser ≥18)
3. Limpiar cache de Vite: `rm -rf node_modules/.vite`

## Referencias

- [React 18 Docs](https://react.dev/)
- [Socket.IO Client](https://socket.io/docs/v4/client-api/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [React Markdown](https://github.com/remarkjs/react-markdown)
- [Vite](https://vitejs.dev/)
