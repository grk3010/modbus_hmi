from nicegui import ui

def main():
    with ui.expansion() as exp:
        with exp.add_slot('header'):
            ui.label("Custom Header!")
            ui.icon('star')
        
        ui.label("This is the body")

    ui.run(port=8081, show=False)

main()
