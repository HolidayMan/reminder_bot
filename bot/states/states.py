from enum import Enum
class States(Enum):
    S_CHOOSE_MENU_OPT = "states.choose_menu_option"
    S_CHOOSE_MAILING_MENU_OPT = "states.choose_mailing_menu_opt"
    S_PAGINATE_EVENTS = "state.paginate_events"
    S_PAGINATE_TZ = "states.paginate_tz"
    S_LESS_19_00 = "states.sleep_calc_less_19_00"
    S_AFTER_20_00 = "states.sleep_calc_after_20_00"
    S_HOW_LONG_I_WILL_SLEEP = "states.sleep_calc_how_long_i_will_sleep"
    S_SLEEP_PHASES = "states.sleep_calc_sleep_phases"
