import questionary
import sys

def selectMenu(title: str, options):
    if isinstance(options, dict):
        choices = [questionary.Choice(key, val) for key, val in options.items()]
        choices.append(questionary.Choice("Quit", "Quit", shortcut_key="q"))
    else:
        choices = list(options)
        choices.append("Quit")

    style = questionary.Style([
        ("question", "fg:#00ffff bold"),
        ("answer", "fg:#7cb7ff bold"),
        ("pointer", "fg:#ed254e bold"),
        ("highlighted", "fg:#ffcc00 bold")
    ])
    selected = questionary.select(title, choices, instruction=" ", style=style).ask()
    if selected == "Quit":
        sys.exit()
    return selected