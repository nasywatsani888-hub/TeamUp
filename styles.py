# styles.py — semua tampilan (stylesheet) dikumpulkan di sini
import os
from config import *

CHECK_ICON = os.path.join(ASSETS_DIR, "icons", "check.png").replace("\\", "/")

APP_STYLE = f"""
QWidget {{
    background: transparent;
    color: {COLOR_TEXT};
    font-family: 'Poppins', 'Segoe UI', Arial, sans-serif;
    font-size: 16px;
}}
QMainWindow, QDialog {{ background-color: white; }}
#Page {{ background-color: {COLOR_BG}; }}
QLineEdit, QTextEdit {{
    background-color: white;
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 14px 16px;
}}
QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {COLOR_PRIMARY}; }}
QCheckBox {{ spacing: 12px; }}
QCheckBox::indicator {{
    width: 24px; height: 24px;
    border: 1px solid {COLOR_BORDER}; border-radius: 6px; background: white;
}}
QCheckBox::indicator:checked {{
    background: {COLOR_PRIMARY}; border: 1px solid {COLOR_PRIMARY};
    image: url({CHECK_ICON});
}}
QMessageBox QLabel {{ font-size: 14px; }}
"""

TITLE_STYLE = f"font-size: 30px; font-weight: bold; color: {COLOR_NAVY};"
SUBTITLE_STYLE = f"font-size: 16px; color: {COLOR_SUBTEXT};"
LABEL_STYLE = f"font-size: 16px; font-weight: bold; color: {COLOR_NAVY};"
ERROR_STYLE = f"color: {COLOR_ERROR}; font-size: 14px;"
SUCCESS_STYLE = f"color: {COLOR_SUCCESS}; font-size: 14px;"
CHIP_STYLE = f"background-color: #E3F1FB; color: {COLOR_PRIMARY}; border-radius: 14px; padding: 6px 14px; font-size: 14px;"

PRIMARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLOR_PRIMARY};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 18px 20px;
    font-size: 18px;
    font-weight: bold;
}}
QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
"""


def link_button_style(size=16, bold=True):
    weight = "bold" if bold else "normal"
    return f"""
QPushButton {{
    background: transparent; color: {COLOR_PRIMARY}; border: none; padding: 0;
    font-size: {size}px; font-weight: {weight};
}}
QPushButton:hover {{ text-decoration: underline; }}
"""


OUTLINE_BUTTON_STYLE = f"""
QPushButton {{
    background: transparent;
    color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 14px;
}}
QPushButton:hover {{ background-color: #E3F1FB; }}
"""

LEFT_PANEL_STYLE = f"#LeftPanel {{ background-color: {COLOR_LEFT_BG}; }}"
RIGHT_PANEL_STYLE = "#RightPanel { background-color: white; }"

TABS_STYLE = f"""
#Tabs {{ background-color: #EEF3F7; border-radius: 12px; }}
#Tabs QPushButton {{
    background: transparent; border: none; border-radius: 10px;
    padding: 10px 34px; color: {COLOR_SUBTEXT}; font-size: 16px;
}}
#Tabs QPushButton[active="true"] {{
    background-color: white; color: {COLOR_NAVY}; font-weight: bold;
}}
"""

PASSWORD_FIELD_STYLE = f"""
#PasswordField {{
    background-color: white;
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
#PasswordField QLineEdit {{ border: none; background: transparent; padding: 14px 8px 14px 16px; }}
#PasswordField QPushButton {{ border: none; background: transparent; }}
"""

OTP_BOX_STYLE = f"""
QLineEdit {{
    background-color: white;
    border: 1px solid #9FB0C8;
    border-radius: 10px;
    font-size: 28px;
    font-weight: bold;
    padding: 0;
}}
QLineEdit:focus {{ border: 2px solid {COLOR_PRIMARY}; }}
"""


# ---------- Dashboard ----------
SIDEBAR_STYLE = f"""
#Sidebar {{ background-color: white; border-right: 1px solid #E5E7EB; }}
#Sidebar QPushButton {{
    background-color: #E4F6FD; color: {COLOR_NAVY}; border: none; border-radius: 16px;
    padding: 12px 14px; text-align: left; font-size: 15px; font-weight: bold;
}}
#Sidebar QPushButton:hover {{ background-color: #CFEFFC; }}
#Sidebar QPushButton[active="true"] {{ background-color: #FFC71F; }}
#Sidebar QPushButton[danger="true"][active="true"] {{ background-color: #F4A6A6; }}
"""

SEARCH_STYLE = "#SearchBar { background-color: #E4F6FD; border: none; border-radius: 22px; padding: 12px 18px; font-size: 15px; }"
BANNER_STYLE = "#Banner { background-color: #A8E4FB; border-radius: 24px; }"
BANNER_BUTTON_STYLE = """
QPushButton { background-color: #4FC8F7; color: white; border: none; border-radius: 22px;
              padding: 14px 44px; font-size: 16px; font-weight: bold; }
QPushButton:hover { background-color: #33B9EE; }
"""
LOMBA_CARD_STYLE = "#LombaCard { background-color: #FFE08F; border-radius: 20px; }"
TAG_STYLE = f"background-color: #FFD04D; color: {COLOR_NAVY}; border-radius: 12px; padding: 4px 16px; font-size: 13px; font-weight: bold;"
DETAIL_BUTTON_STYLE = """
QPushButton { background-color: #FFB733; color: white; border: none; border-radius: 12px;
              padding: 8px 18px; font-size: 13px; font-weight: bold; }
QPushButton:hover { background-color: #F5A623; }
"""
PROFILE_CARD_STYLE = "#ProfileCard { background-color: #CDEBF7; border-radius: 24px; }"
EDIT_BUTTON_STYLE = """
QPushButton { background-color: #86D6F5; color: white; border: none; border-radius: 14px;
              padding: 8px 26px; font-size: 14px; font-weight: bold; }
QPushButton:hover { background-color: #6BC8EE; }
"""
SIDEBAR_EDIT_BUTTON_STYLE = """
QPushButton { background-color: #A8E4FB; color: #0A7BCB; border: none; border-radius: 10px;
              padding: 3px 14px; font-size: 12px; font-weight: bold; text-align: center; }
QPushButton:hover { background-color: #86D6F5; }
"""
DEADLINE_CARD_STYLE = "#DeadlineCard { background-color: #F6A9C4; border-radius: 24px; }"
DEADLINE_ITEM_STYLE = "#DeadlineItem { background-color: white; border-radius: 8px; }"


# ---------- Rekan Tim & Profil Rekan ----------
DROPDOWN_BUTTON_STYLE = f"""
QPushButton {{
    background-color: white; color: {COLOR_NAVY}; border: 1px solid {COLOR_BORDER};
    border-radius: 16px; padding: 7px 18px; font-size: 13px; text-align: left;
}}
QPushButton:hover {{ background-color: #F0FAFF; }}
QPushButton[selected="true"] {{ border: 1px solid {COLOR_PRIMARY}; }}
"""

# Warna popup filter: "blue" untuk Rekan Tim, "yellow" untuk Lomba
POPUP_ACCENTS = {
    "blue": {"border": "#86D6F5", "title": "#4FC8F7", "button": "#4FC8F7", "hover": "#33B9EE", "soft": "#E4F6FD"},
    "yellow": {"border": "#FFD04D", "title": "#F5A000", "button": "#FFB733", "hover": "#F5A623", "soft": "#FFF3D1"},
}


def popup_style(accent):
    c = POPUP_ACCENTS[accent]
    return f"""
#PopupBox {{ background-color: white; border: 2px solid {c["border"]}; border-radius: 18px; }}
#PopupTitle {{ color: {c["title"]}; font-size: 14px; font-weight: bold; }}
#PopupBox QCheckBox {{ font-size: 14px; color: {COLOR_NAVY}; }}
#PopupBox QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; }}
#PopupBox QCheckBox::indicator:checked {{
    background: {c["button"]}; border: 1px solid {c["button"]}; image: url({CHECK_ICON});
}}
"""


def popup_reset_style(accent):
    c = POPUP_ACCENTS[accent]
    return f"""
QPushButton {{ background: white; color: {c["title"]}; border: 1px solid {c["border"]}; border-radius: 14px;
               padding: 7px 0; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background-color: {c["soft"]}; }}
"""


def popup_apply_style(accent):
    c = POPUP_ACCENTS[accent]
    return f"""
QPushButton {{ background-color: {c["button"]}; color: white; border: none; border-radius: 14px;
               padding: 7px 0; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background-color: {c["hover"]}; }}
"""


PARTNER_CARD_STYLE = "#PartnerCard { background-color: #DDF1FA; border: 2px solid #4FC8F7; border-radius: 20px; }"
CARD_CHIP_STYLE = f"background-color: white; color: {COLOR_PRIMARY}; border: 1px solid #86D6F5; border-radius: 10px; padding: 2px 10px; font-size: 11px;"
VISIT_BUTTON_STYLE = f"""
QPushButton {{ background-color: {COLOR_NAVY}; color: white; border: none; border-radius: 12px;
               padding: 7px 18px; font-size: 12px; font-weight: bold; }}
QPushButton:hover {{ background-color: #0B2456; }}
"""

# ---------- Detail Lomba: panel "Rekomendasi Rekan" ----------
SUGGESTED_PARTNER_BOX_STYLE = "#SuggestedPartnerBox { background-color: #CDEBF7; border-radius: 24px; }"
SUGGESTED_PARTNER_CARD_STYLE = "#SuggestedPartnerCard { background-color: white; border-radius: 16px; }"

PROFILE_HEADER_STYLE = "#ProfileHeader { background-color: white; }"
PROFILE_INFO_STYLE = "#ProfileInfo { background-color: white; }"
BACK_BUTTON_STYLE = "QPushButton { background: transparent; border: none; padding: 4px; } QPushButton:hover { background-color: #B5E0F2; border-radius: 12px; }"
INFO_PILL_STYLE = f"background-color: #FFC71F; color: {COLOR_NAVY}; border-radius: 12px; padding: 4px 16px; font-size: 13px;"
SECTION_TITLE_STYLE = f"background-color: white; color: {COLOR_NAVY}; border: 1px solid {COLOR_NAVY}; border-radius: 10px; padding: 1px 20px; font-size: 12px; font-weight: bold;"
SECTION_CARD_STYLE = "#SectionCard { background-color: white; border: 1px solid #CDEBF7; border-radius: 14px; }"
PROFILE_PHOTO_FRAME_STYLE = "#PhotoFrame { background-color: white; border: 3px solid #CDEBF7; border-radius: 18px; }"


# ---------- Detail Lomba ----------
DETAIL_HEADER_STYLE = "#DetailHeader { background-color: white; }"
VERIFIED_BADGE_STYLE = f"background-color: #DDF1FA; color: {COLOR_PRIMARY}; border-radius: 10px; padding: 3px 12px; font-size: 12px; font-weight: bold;"
DAYS_BADGE_STYLE = "background-color: #FFD6D6; color: #E53935; border-radius: 10px; padding: 3px 12px; font-size: 12px; font-weight: bold;"
INFO_TITLE_STYLE = f"background-color: white; color: #F5A623; border: 1px solid #F5D77F; border-radius: 10px; padding: 2px 18px; font-size: 12px; font-weight: bold;"
INFO_BOX_STYLE = "#InfoBox { background-color: #FFE9A8; border: 1px solid #F5D77F; border-radius: 14px; }"
DETAIL_BOX_STYLE = "#DetailBox { background-color: white; border: 1px solid #F5D77F; border-radius: 14px; }"
LOMBA_LINK_STYLE = f"font-size: 14px; color: {COLOR_PRIMARY};"


# ---------- Notifikasi ----------
NOTIF_TAB_STYLE = f"""
QPushButton {{
    background: white; color: {COLOR_PRIMARY}; border: 1px solid {COLOR_PRIMARY};
    border-radius: 14px; padding: 5px 26px; font-size: 13px; font-weight: bold;
}}
QPushButton[active="true"] {{ background-color: {COLOR_PRIMARY}; color: white; }}
"""
NOTIF_ITEM_STYLE = """
#NotifItem { background-color: white; border: 2px solid #4FC8F7; border-radius: 16px; }
#NotifItem[unread="true"] { background-color: #DDF1FA; border: 2px solid #DDF1FA; }
"""
NOTIF_GROUP_STYLE = f"font-size: 13px; font-weight: bold; color: {COLOR_PRIMARY};"


# ---------- Riwayat ----------
HISTORY_ITEM_STYLE = """
#HistoryItem { background-color: #DDF1FA; border-radius: 16px; }
#HistoryItem:hover { background-color: #CDEBF7; }
"""


# ---------- Edit Profil ----------
EDIT_BANNER_STYLE = "#EditBanner { background-color: #E6FAFF; }"
EDIT_PAGE_STYLE = f"""
#EditForm QLineEdit, #EditForm QTextEdit {{
    padding: 9px 12px; font-size: 13px; border-radius: 4px;
}}
#EditForm QLineEdit[readOnly="true"] {{ background-color: #F3F6FA; color: {COLOR_SUBTEXT}; }}
#EditForm QLabel[role="field"] {{ font-size: 12px; font-weight: bold; color: {COLOR_TEXT}; }}
"""
CAMERA_BUTTON_STYLE = f"QPushButton {{ background-color: {COLOR_PRIMARY}; border: 2px solid white; border-radius: 12px; }}"
AVATAR_CIRCLE_STYLE = "background-color: white; border: 1px solid #DCE6EE; border-radius: 45px;"
EDIT_TITLE_STYLE = f"font-size: 16px; font-weight: bold; color: {COLOR_PRIMARY};"
EDIT_SUBTITLE_STYLE = f"font-size: 12px; color: {COLOR_TEXT};"
SKILL_CHIP_STYLE = f"""
#SkillChip {{ background-color: #E3F1FB; border: 1px solid #86D6F5; border-radius: 15px; }}
#SkillChip QLabel {{ color: {COLOR_PRIMARY}; font-size: 12px; }}
#SkillChip QPushButton {{ background: transparent; border: none; padding: 0; }}
"""
ADD_DASHED_STYLE = f"""
QPushButton {{ background: white; color: #9FB0C8; border: 1px dashed #9FB0C8; border-radius: 15px;
               padding: 5px 14px; font-size: 12px; }}
QPushButton:hover {{ color: {COLOR_PRIMARY}; border-color: {COLOR_PRIMARY}; }}
"""
EXP_ROW_STYLE = f"""
#ExpRow {{ background-color: white; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}
#ExpRow QLabel {{ font-size: 12px; }}
#ExpRow QPushButton {{ background: transparent; border: none; padding: 2px; }}
"""
EDIT_RESET_STYLE = f"""
QPushButton {{ background: white; color: {COLOR_PRIMARY}; border: 1px solid {COLOR_PRIMARY};
               border-radius: 12px; padding: 8px 30px; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background-color: #E3F1FB; }}
"""
EDIT_SAVE_STYLE = f"""
QPushButton {{ background-color: {COLOR_PRIMARY}; color: white; border: none;
               border-radius: 12px; padding: 9px 32px; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
"""
ROUND_PLUS_STYLE = f"""
QPushButton {{ background: transparent; border: 1px solid {COLOR_BORDER}; border-radius: 13px; }}
QPushButton:hover {{ background-color: #E3F1FB; border-color: {COLOR_PRIMARY}; }}
"""

# ---------- Dialog Upload File ----------
DROP_ZONE_STYLE = f"""
#DropZone {{ background-color: white; border: 2px dashed #9FB0C8; border-radius: 16px; }}
#DropZone[hover="true"] {{ border-color: {COLOR_PRIMARY}; background-color: #F0FAFF; }}
"""
UPLOAD_BUTTON_STYLE = f"""
QPushButton {{ background-color: {COLOR_PRIMARY}; color: white; border: none; border-radius: 10px;
               padding: 8px 26px; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
QPushButton:disabled {{ background-color: #9AA5B1; }}
"""


# ---------- Pusat Bantuan & Keluar ----------
CARD_BORDER_COLOR = "#264D5E"
MODAL_CARD_STYLE = f"#ModalCard {{ background-color: white; border: 2px solid {CARD_BORDER_COLOR}; border-radius: 16px; }}"
OVERLAY_STYLE = "#Overlay { background-color: rgba(15, 30, 60, 70); }"
CANCEL_SMALL_STYLE = """
QPushButton { background: white; color: #8A97A6; border: 1px solid #B8C2CC; border-radius: 9px;
              padding: 2px 10px; font-size: 11px; }
QPushButton:hover { background-color: #F3F6FA; }
"""
HELP_ICON_STYLE = "background-color: #E6F6FD; border-radius: 26px;"
HELP_NUMBER_STYLE = f"font-size: 26px; font-weight: bold; color: {COLOR_NAVY};"
CALL_BUTTON_STYLE = """
QPushButton { background-color: #3374C7; color: white; border: none; border-radius: 10px;
              padding: 8px 20px; font-size: 12px; font-weight: bold; }
QPushButton:hover { background-color: #2A63AD; }
"""
LOGOUT_ICON_STYLE = "background-color: #F4A3A3; border-radius: 26px;"
LOGOUT_CANCEL_STYLE = """
QPushButton { background: white; color: #8A97A6; border: 1px solid #B8C2CC; border-radius: 10px;
              padding: 7px 0; font-size: 12px; font-weight: bold; }
QPushButton:hover { background-color: #F3F6FA; }
"""
LOGOUT_CONFIRM_STYLE = """
QPushButton { background-color: #D9534F; color: white; border: none; border-radius: 10px;
              padding: 7px 0; font-size: 12px; font-weight: bold; }
QPushButton:hover { background-color: #C4423E; }
"""


# ---------- Unggah Postingan -> Postingan Saya ----------
POST_TAB_STYLE = f"""
QPushButton {{ background-color: white; color: #2557B0; border: 1px solid #2557B0;
              border-radius: 12px; padding: 3px 16px; font-size: 12px; }}
QPushButton:hover {{ background-color: #EAF1FC; }}
QPushButton:checked {{ background-color: #2557B0; color: white; font-weight: bold; }}
"""
POST_CHIP_STYLE = f"""
QPushButton {{ background-color: white; color: #2557B0; border: 1px solid #2557B0;
              border-radius: 12px; padding: 3px 14px; font-size: 12px; }}
QPushButton:hover {{ background-color: #EAF1FC; }}
QPushButton:checked {{ background-color: #2557B0; color: white; font-weight: bold; }}
"""
POST_ITEM_STYLE = "#PostItem { background-color: white; border: 1px solid #C9CED6; border-radius: 4px; }"
POST_THUMB_STYLE = "background-color: #EAF7FD; border-radius: 4px;"
# status -> (warna latar, warna teks) badge di sisi kanan baris postingan
POST_STATUS_COLORS = {
    "Disetujui": ("#DDEBC8", "#4B7A2A"),
    "Ditangguhkan": ("#FFEFC2", "#E39A1F"),
    "Revisi": ("#EBA33A", "#FFFFFF"),
    "Ditolak": ("#F7C6C6", "#8E2A2A"),
}


# ---------- Formulir Unggah Info Lomba ----------
POST_FORM_STYLE = f"""
#PostForm QLineEdit, #PostForm QTextEdit, #PostForm QDateEdit, #PostForm QComboBox {{
    background-color: white; border: 1px solid #B8C2CC; border-radius: 3px;
    padding: 8px 10px; font-size: 12px; color: {COLOR_TEXT};
}}
#PostForm QLineEdit:focus, #PostForm QTextEdit:focus, #PostForm QDateEdit:focus, #PostForm QComboBox:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}
#PostForm QLineEdit[invalid="true"] {{ background-color: #F7C6C6; border: 1px solid #E57373; }}
#PostForm QComboBox::drop-down, #PostForm QDateEdit::drop-down {{ border: none; width: 26px; }}
#PostForm QLabel[role="section"] {{ font-size: 14px; font-weight: bold; color: {COLOR_NAVY}; }}
#PostForm QLabel[role="field"] {{ font-size: 11px; font-weight: bold; color: {COLOR_NAVY}; }}
#PostForm QLabel[role="hint"] {{ font-size: 10px; color: {COLOR_SUBTEXT}; }}
"""
POST_BLUE_BUTTON_STYLE = """
QPushButton { background-color: #3374C7; color: white; border: none; border-radius: 10px;
              padding: 9px 26px; font-size: 12px; font-weight: bold; }
QPushButton:hover { background-color: #2A63AD; }
"""
POST_OUTLINE_BUTTON_STYLE = f"""
QPushButton {{ background-color: white; color: {COLOR_NAVY}; border: 1px solid #B8C2CC; border-radius: 10px;
              padding: 9px 26px; font-size: 12px; font-weight: bold; }}
QPushButton:hover {{ background-color: #F3F6FA; }}
"""
POST_TRASH_BUTTON_STYLE = """
QPushButton { background-color: white; border: 1px solid #E57373; border-radius: 10px; padding: 8px 12px; }
QPushButton:hover { background-color: #FDECEC; }
"""

# ---------- Detail Postingan ----------
POST_CATEGORY_CHIP_STYLE = f"background-color: #E3F1FB; color: {COLOR_PRIMARY}; border: 1px solid #86D6F5; border-radius: 8px; padding: 2px 10px; font-size: 11px;"
POST_BAND_COLORS = {          # warna pita di atas halaman detail, sesuai status
    "Ditangguhkan": "#F7DF9B",
    "Disetujui": "#DDEFC9",
    "Revisi": "#EBA33A",
    "Ditolak": "#E8352A",
}
POST_BAND_DARK = ("Revisi", "Ditolak")   # pita gelap -> panah kembali berwarna putih


def post_box_style(background, border):
    """Kotak catatan / peringatan di halaman detail postingan."""
    return f"#PostBox {{ background-color: {background}; border: 1px solid {border}; border-radius: 8px; }}"


POST_BOX_YELLOW = post_box_style("#FFF1C9", "#F5C84B")
POST_BOX_RED = post_box_style("#F7C6C6", "#E57373")
POST_BOX_GREEN = post_box_style("#E4F5D8", "#9ED17B")
POST_STAT_DIVIDER_STYLE = "background-color: #C9CED6;"
