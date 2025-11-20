#!/bin/bash
# Run E2E test with live dashboard visualization

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     E2E TEST + DASHBOARD EN VIVO                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if in tmux or screen
if [ -n "$TMUX" ] || [ -n "$STY" ]; then
    echo "✓ Detected terminal multiplexer - perfect for split view"
    echo ""
    echo "INSTRUCCIONES:"
    echo "1. En este panel: Se va a ejecutar el DASHBOARD"
    echo "2. Abrí otro panel/ventana y ejecutá:"
    echo "   python3 tests/e2e/real_e2e_with_dashboard.py"
    echo ""
    echo "3. VAS A VER EL PROGRESO EN TIEMPO REAL EN EL DASHBOARD!"
    echo ""
    read -p "Presioná ENTER cuando estés listo para ver el dashboard..."

    # Run dashboard
    python3 tests/e2e/progress_dashboard.py --mock --duration 120

else
    echo "⚠️  No estás en tmux/screen. Vas a necesitar 2 terminales:"
    echo ""
    echo "TERMINAL 1 (esta):"
    echo "  python3 tests/e2e/progress_dashboard.py --mock --duration 120"
    echo ""
    echo "TERMINAL 2 (otra que abras):"
    echo "  cd /home/kwar/code/agentic-ai"
    echo "  python3 tests/e2e/real_e2e_with_dashboard.py"
    echo ""
    echo "O mejor aún, usá tmux:"
    echo "  tmux"
    echo "  # Luego dividí la pantalla con Ctrl+b %"
    echo ""
    read -p "¿Querés ejecutar el dashboard ahora? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        python3 tests/e2e/progress_dashboard.py --mock --duration 120
    fi
fi
