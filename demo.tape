# Regenerate with: vhs demo.tape
Output assets/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1100
Set Height 820
Set Padding 24
Set Theme "Dracula"

# Hidden setup: put the installed CLI on PATH and clear the screen.
Hide
Type `export PATH="$PWD/.venv/bin:$PATH"`
Enter
Type "clear"
Enter
Sleep 1s
Show

Type "parity-monitor examples/backtest.csv examples/live.csv"
Sleep 1s
Enter
Sleep 5s
