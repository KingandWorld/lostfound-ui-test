"""截图工具：统一把页面截图附加到 Allure 报告（Day15）。

base_page.screenshot()（保存文件 + 附件）与 conftest 的失败自动截图
（内存截图附件）都复用本模块，保证报告附件风格一致。
"""

import allure


def attach_screenshot(page, name: str = "页面截图", full_page: bool = True):
    """截图（内存）并附加到 Allure（PNG 附件）。

    失败时返回 None 不抛错——截图只是留证，不应影响用例结果。
    """
    try:
        data = page.screenshot(full_page=full_page)
        allure.attach(data, name=name, attachment_type=allure.attachment_type.PNG)
        return data
    except Exception:
        return None
