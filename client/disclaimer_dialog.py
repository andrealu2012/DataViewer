"""First-run risk disclaimer for the desktop client."""

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)


DISCLAIMER_ACCEPTED_KEY = "legal/disclaimer_accepted"


class DisclaimerDialog(QDialog):
    """Require explicit acceptance before the client can be used."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用须知及风险免责声明")
        self.setModal(True)
        self.setMinimumSize(620, 480)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        title = QLabel("使用须知及风险免责声明")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 8px;")

        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        content.setHtml(
            """
            <p>在使用本软件前，请您认真阅读并充分理解以下条款：</p>
            <ol>
              <li><b>信息用途：</b>本软件展示的股票行情、价格、涨跌幅及其他相关信息，
              仅供学习、研究和信息参考，不构成任何形式的投资建议、交易依据、收益承诺或要约。</li>
              <li><b>数据风险：</b>受数据源、网络通信、服务器状态、软件缺陷、系统时间及其他因素影响，
              本软件所展示的信息可能存在延迟、遗漏、错误、中断或与实际行情不一致的情况。
              您不应将本软件作为作出投资决策的唯一依据。</li>
              <li><b>投资风险：</b>证券市场具有风险，投资可能造成部分或全部本金损失。
              您应根据自身风险承受能力独立判断、审慎决策，并自行核验相关信息。</li>
              <li><b>责任限制：</b>在法律允许的最大范围内，软件作者及相关提供方不对因使用、
              无法使用或信赖本软件及其展示信息而产生的任何直接或间接损失承担责任，
              包括但不限于交易损失、利润损失、数据损失或机会损失。</li>
              <li><b>用户责任：</b>您对使用本软件所进行的全部操作及其后果承担责任。
              如您不同意上述条款，请立即停止使用并退出本软件。</li>
            </ol>
            <p><b>点击“同意并继续”，即表示您已阅读、理解并自愿接受上述全部条款。</b></p>
            """
        )

        buttons = QDialogButtonBox()
        disagree_button = buttons.addButton("不同意并退出", QDialogButtonBox.ButtonRole.RejectRole)
        agree_button = buttons.addButton("同意并继续", QDialogButtonBox.ButtonRole.AcceptRole)
        agree_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(content)
        layout.addWidget(buttons)

def ensure_disclaimer_accepted(settings: QSettings | None = None) -> bool:
    """Return True when previously or newly accepted; never persist rejection."""
    settings = settings or QSettings()
    if settings.value(DISCLAIMER_ACCEPTED_KEY, False, type=bool):
        return True

    dialog = DisclaimerDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    settings.setValue(DISCLAIMER_ACCEPTED_KEY, True)
    settings.sync()
    return True
