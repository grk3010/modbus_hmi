from nicegui import ui

ui.add_head_html("""
<style>
.custom-toggle {
    appearance: none;
    -webkit-appearance: none;
    width: 100px;
    height: 40px;
    border-radius: 40px;
    background: transparent;
    border: 2px solid white;
    outline: none;
    cursor: pointer;
    position: relative;
    transition: all 0.3s;
}
.custom-toggle::before {
    content: 'CLOSED';
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: white;
    font-weight: bold;
    font-size: 14px;
    transition: opacity 0.3s;
}
.custom-toggle::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 3px;
    width: 32px;
    height: 32px;
    background: white;
    border-radius: 50%;
    transition: all 0.3s;
}
.custom-toggle:checked {
    background: #2dd4bf;
    border-color: #2dd4bf;
}
.custom-toggle:checked::before {
    content: 'OPEN';
    right: auto;
    left: 15px;
}
.custom-toggle:checked::after {
    transform: translateX(58px);
}
</style>
""")

def on_change(e):
    # e.args might be a dict or simply the event
    print(e.sender.value)

ui.label('Test Toggle')
# In NiceGUI, ui.input or standard ui.element
# If we do ui.element('input') we can't easily auto-bind `checked`.
# Better to use GenericElement if needed or intercept click.

with ui.element('div').classes('p-10 bg-gray-800'):
    # Let's try binding checked property
    inp = ui.element('input').props('type="checkbox"').classes('custom-toggle')
    # Use Vue v-model or similar? NiceGUI doesn't support v-model deeply on standard elements.
    
    # We can use vue @change
    inp.on('change', lambda e: ui.notify(f"Checkbox changed"))

ui.run(port=8082, dark=True)
