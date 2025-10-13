# Devmatrix Web UI

Simple, responsive web interface for workflow orchestration built with HTML, Vanilla JavaScript, and Tailwind CSS.

## Features

### 📋 Workflows Management
- List all workflows with task details
- Create new workflows with JSON task definitions
- Delete workflows
- Start workflow executions
- View task dependencies

### ▶️ Executions Monitoring
- Real-time execution status tracking
- Auto-refresh every 5 seconds (toggleable)
- Cancel running executions
- Delete execution records
- Status indicators (pending, running, completed, failed, cancelled)

### 📊 Metrics Dashboard
- Total workflows count
- Total executions count
- Average execution time
- Success rate percentage
- Executions breakdown by status with progress bars

### 🏥 Health Monitoring
- Real-time system health indicator in navigation
- Color-coded status (green = healthy, yellow = degraded, red = unhealthy)
- Auto-refresh every 30 seconds

## Technology Stack

- **HTML5**: Semantic markup
- **Tailwind CSS**: Utility-first CSS framework (CDN)
- **Vanilla JavaScript**: No framework dependencies
- **Font Awesome**: Icon library (CDN)
- **Fetch API**: REST API integration

## File Structure

```
src/api/static/
├── index.html       # Main HTML structure with all UI components
├── js/
│   └── app.js       # Application logic and API integration
├── css/             # Custom styles (if needed)
└── assets/          # Images and other assets
```

## Key Components

### Tab Navigation
- **Workflows**: Manage workflow definitions
- **Executions**: Monitor workflow executions
- **Metrics**: View system metrics and statistics

### Modals
- **Create Workflow**: Form for creating new workflows with JSON task editor

### Toast Notifications
- Success messages (green)
- Error messages (red)
- Info messages (blue)
- Auto-dismiss after 5 seconds

## API Integration

All API calls use the Fetch API with `/api/v1` base URL:

### Workflows
- `GET /api/v1/workflows` - List all workflows
- `POST /api/v1/workflows` - Create workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Executions
- `GET /api/v1/executions` - List all executions
- `POST /api/v1/executions` - Start execution
- `POST /api/v1/executions/{id}/cancel` - Cancel execution
- `DELETE /api/v1/executions/{id}` - Delete execution

### Metrics
- `GET /api/v1/metrics/summary` - Get metrics summary

### Health
- `GET /api/v1/health` - System health check

## Running the UI

### Development

The UI is served automatically by the FastAPI application:

```bash
# Start the API server
python -m src.api.main

# Or with uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit: http://localhost:8000

### Production

The UI is bundled with the API server, no separate build step required.

For production deployment:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Features in Detail

### Workflows Tab

**List View:**
- Card-based layout
- Expandable task details
- Quick actions: Run, Delete
- Empty state with call-to-action

**Create Workflow:**
- Form validation
- JSON syntax highlighting in textarea
- Example task structure provided
- Real-time error feedback

### Executions Tab

**List View:**
- Status badges with icons
- Priority display
- Execution/Workflow ID display
- Timestamps (created, started, completed)
- Error messages display
- Quick actions: Cancel, Delete

**Auto-refresh:**
- Toggle on/off
- 5-second interval
- Only active when Executions tab is visible
- Manual refresh button

### Metrics Tab

**Metric Cards:**
- Total Workflows (blue)
- Total Executions (green)
- Average Time (yellow)
- Success Rate (purple)

**Status Breakdown:**
- Progress bars for each status
- Percentage calculations
- Color-coded (completed=green, running=blue, pending=yellow, failed=red, cancelled=gray)

## Customization

### Colors
Tailwind CSS utility classes used throughout. To customize colors, modify class names in `index.html`:

```html
<!-- Example: Change primary color from blue to purple -->
<button class="bg-purple-600 hover:bg-purple-700">
```

### Auto-refresh Interval
Edit in `app.js`:

```javascript
startAutoRefresh() {
    autoRefreshInterval = setInterval(() => {
        loadExecutions();
    }, 5000); // Change to desired milliseconds
}
```

### Health Check Interval
Edit in `app.js`:

```javascript
setInterval(checkHealth, 30000); // Change to desired milliseconds
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires:
- ES6 support
- Fetch API
- Async/Await
- CSS Grid & Flexbox

## Troubleshooting

### UI doesn't load
- Check FastAPI server is running
- Verify static files exist in `src/api/static/`
- Check browser console for errors
- Ensure CORS is configured

### API calls fail
- Verify API server is accessible
- Check API base URL in `app.js`
- Check browser network tab for errors
- Verify API endpoints are responding

### Styles not working
- Check Tailwind CSS CDN is accessible
- Verify internet connection (CDN dependencies)
- Check browser console for CSS errors

### Icons not showing
- Check Font Awesome CDN is accessible
- Verify internet connection
- Check browser console for font errors

## Security Considerations

### Production Deployment
- Use HTTPS in production
- Configure proper CORS origins
- Implement authentication/authorization
- Validate all user inputs
- Sanitize displayed data (currently using `escapeHtml()`)
- Add rate limiting
- Use CSP headers

### Current Security Features
- HTML escaping for user content
- JSON validation in workflow creation
- Confirmation dialogs for destructive actions
- Error message sanitization

## Performance Optimization

### Current Optimizations
- Auto-refresh only when tab is visible
- Lightweight vanilla JavaScript (no framework overhead)
- CDN-hosted dependencies (cached by browser)
- Minimal API calls (on-demand loading)

### Future Improvements
- Implement pagination for large lists
- Add local storage for user preferences
- WebSocket for real-time updates (instead of polling)
- Service worker for offline support
- Bundle and minify assets

## Accessibility

### Current Features
- Semantic HTML
- Keyboard navigation support
- Color-coded status indicators
- Loading states with spinners
- Clear error messages

### Future Improvements
- ARIA labels for screen readers
- Focus management in modals
- High contrast mode support
- Keyboard shortcuts
- Skip navigation links

## Contributing

To add new features to the UI:

1. Update `index.html` for new components
2. Add JavaScript functions in `app.js`
3. Follow existing patterns for API integration
4. Test across browsers
5. Update this README

## License

See main project LICENSE file.
