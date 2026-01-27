from transflate.translator import JsonTranslator

translator = JsonTranslator("locales")

def get_translator():
    return translator