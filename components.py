import asyncio
from nicegui import ui
from shared_state import settings, save_settings

class ValveToggle(ui.element):
    def __init__(self, port_num, initial_state=False, client=None):
        super().__init__('div')
        self.port_num = port_num
        self.state = initial_state
        self.modbus_client = client
        self.classes('relative inline-flex items-center w-[168px] h-[72px] rounded-full cursor-pointer transition-all duration-300 border-4 border-solid shadow-sm select-none shrink-0')
        self.on('click', self.toggle)
        
        with self:
            self.thumb = ui.element('div').classes('absolute w-[54px] h-[54px] bg-white rounded-full shadow-md transition-all duration-300 z-10')
            self.lbl = ui.label('').classes('absolute text-white font-bold text-lg tracking-wider pointer-events-none transition-all duration-300 z-0')
            
        self._update_appearance()

    def toggle(self):
        self.state = not self.state
        self._update_appearance()
        if self.modbus_client:
            asyncio.create_task(self.modbus_client.write_valve(self.port_num, self.state))

    def _update_appearance(self):
        if self.state:
            self.classes(remove='border-white bg-[#303030]', add='border-[#20c997] bg-[#20c997]')
            self.thumb.classes(remove='left-[8px]', add='left-[102px]')
            self.lbl.set_text('OPEN')
            self.lbl.classes(remove='right-[16px]', add='left-[16px]')
        else:
            self.classes(remove='border-[#20c997] bg-[#20c997]', add='border-white bg-[#303030]')
            self.thumb.classes(remove='left-[102px]', add='left-[8px]')
            self.lbl.set_text('CLOSED')
            self.lbl.classes(remove='left-[16px]', add='right-[16px]')

class SimulationToggle(ui.element):
    def __init__(self, initial_state=False):
        super().__init__('div')
        self.state = initial_state
        self.classes('relative inline-flex items-center w-[168px] h-[72px] rounded-full cursor-pointer transition-all duration-300 border-4 border-solid shadow-sm select-none shrink-0')
        self.on('click', self.toggle)
        
        with self:
            self.thumb = ui.element('div').classes('absolute w-[54px] h-[54px] bg-white rounded-full shadow-md transition-all duration-300 z-10')
            self.lbl = ui.label('').classes('absolute text-white font-bold text-lg tracking-wider pointer-events-none transition-all duration-300 z-0')
            
        self._update_appearance()

    def toggle(self):
        self.state = not self.state
        settings["use_simulation"] = self.state
        save_settings()
        self._update_appearance()

    def _update_appearance(self):
        if self.state:
            self.classes(remove='border-white bg-[#303030]', add='border-[#20c997] bg-[#20c997]')
            self.thumb.classes(remove='left-[8px]', add='left-[102px]')
            self.lbl.set_text('SIM ON')
            self.lbl.classes(remove='right-[16px]', add='left-[16px]')
        else:
            self.classes(remove='border-[#20c997] bg-[#20c997]', add='border-white bg-[#303030]')
            self.thumb.classes(remove='left-[102px]', add='left-[8px]')
            self.lbl.set_text('SIM OFF')
            self.lbl.classes(remove='left-[16px]', add='right-[16px]')
