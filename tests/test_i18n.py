from disk_history.i18n import DEFAULT_LANGUAGE, missing_translation_keys, normalize_language, translate


def test_default_language_is_chinese():
    assert DEFAULT_LANGUAGE == "zh-CN"
    assert normalize_language("unknown") == "zh-CN"


def test_translation_keys_are_complete():
    assert missing_translation_keys() == {}


def test_translate_formats_values():
    assert translate("zh-CN", "label.monitor_total", count=3) == "当前监控规则：3 个"
    assert translate("en", "label.monitor_total", count=3) == "Monitor rules: 3"

