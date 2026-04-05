#!/usr/bin/env python3
"""
Minecraft Username Sniper
自動在指定時間區間內，以設定的間隔嘗試將帳號名稱改為目標名稱。
使用 Bearer Token 直接認證。
"""

import requests
import time
import sys
from datetime import datetime
from typing import Optional, Tuple

MC_PROFILE_URL   = "https://api.minecraftservices.com/minecraft/profile"
MC_NAME_URL      = "https://api.minecraftservices.com/minecraft/profile/name/{name}"
MC_NAMECHECK_URL = "https://api.minecraftservices.com/minecraft/profile/name/{name}/available"


# ═══════════════════════════════════════════════════════════════════
#  名稱操作
# ═══════════════════════════════════════════════════════════════════

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_current_name(token: str) -> str:
    resp = requests.get(MC_PROFILE_URL, headers=auth_headers(token))
    if resp.status_code == 401:
        sys.exit("Bearer Token 無效或已過期，請重新取得。")
    if resp.status_code == 403:
        sys.exit(
            "403 Forbidden：Token 被拒絕。\n"
            "可能原因：\n"
            "  1. 此帳號未購買 Minecraft Java Edition\n"
            "  2. Token 格式錯誤（確認只貼 token 本身，不含 'Bearer ' 前綴）\n"
            f"  回應內容：{resp.text}"
        )
    resp.raise_for_status()
    return resp.json().get("name", "unknown")


def is_name_available(name: str, token: str) -> bool:
    url  = MC_NAMECHECK_URL.format(name=name)
    resp = requests.get(url, headers=auth_headers(token))
    if resp.status_code == 200:
        return resp.json().get("status", "") == "AVAILABLE"
    return False


def attempt_name_change(name: str, token: str) -> Tuple[bool, str]:
    url  = MC_NAME_URL.format(name=name)
    resp = requests.put(url, headers=auth_headers(token))

    if resp.status_code == 200:
        return True, "改名成功！"
    elif resp.status_code == 400:
        return False, "名稱不可用或格式不符"
    elif resp.status_code == 401:
        sys.exit("Bearer Token 無效或已過期，請重新取得。")
    elif resp.status_code == 403:
        try:
            msg = resp.json().get("errorMessage", resp.text)
        except Exception:
            msg = resp.text
        return False, f"禁止改名（冷卻中或其他限制）：{msg}"
    elif resp.status_code == 429:
        return False, "請求過於頻繁，請降低頻率"
    else:
        return False, f"HTTP {resp.status_code}：{resp.text}"


# ═══════════════════════════════════════════════════════════════════
#  輸入工具
# ═══════════════════════════════════════════════════════════════════

def input_str(prompt: str) -> str:
    value = input(prompt).strip()
    if not value:
        sys.exit("未輸入內容，程式結束。")
    return value


def input_float(prompt: str, default: float) -> float:
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"  輸入無效，使用預設值 {default}")
        return default


def input_time(prompt: str) -> Optional[datetime]:
    raw = input(prompt).strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("  格式錯誤，忽略此時間設定。")
        return None


# ═══════════════════════════════════════════════════════════════════
#  主程式
# ═══════════════════════════════════════════════════════════════════

def wait_until(start: Optional[datetime]):
    if start is None:
        return
    if datetime.now() < start:
        print(f"等待開始時間：{start}")
        while datetime.now() < start:
            remaining = (start - datetime.now()).total_seconds()
            print(f"  倒數 {remaining:.1f} 秒...  ", end="\r")
            time.sleep(0.5)
        print()


def main():
    print("=" * 55)
    print("  Minecraft Username Sniper")
    print("=" * 55)

    token       = input_str("Bearer Token：")
    target_name = input_str("目標使用者名稱：")
    interval    = input_float("嘗試間隔（秒，預設 10，可輸入小數如 0.5）：", default=10)
    start_dt    = input_time("開始時間（格式 2026-05-01 08:00:00，直接 Enter = 立即）：")
    end_dt      = input_time("結束時間（格式 2026-05-01 10:00:00，直接 Enter = 不限制）：")

    print()
    print(f"  目標名稱    : {target_name}")
    print(f"  嘗試間隔    : {interval} 秒")
    print(f"  開始時間    : {start_dt or '立即'}")
    print(f"  結束時間    : {end_dt or '無限制'}")
    print("=" * 55)

    # 自動去除意外帶入的前綴
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    print(f"驗證 Bearer Token（前20碼：{token[:20]}...）")
    current = get_current_name(token)
    print(f"目前帳號名稱：{current}\n")

    if current == target_name:
        print("目前名稱已與目標相同，無需更改。")
        return

    wait_until(start_dt)

    attempt = 0
    print(f"開始嘗試搶名：{target_name}\n")

    while True:
        now = datetime.now()

        if end_dt and now > end_dt:
            print(f"\n[{now:%H:%M:%S}] 已超過設定的結束時間，停止嘗試。")
            break

        attempt += 1
        ts = now.strftime("%H:%M:%S")

        available = is_name_available(target_name, token)
        status_str = "可用" if available else "不可用"
        print(f"[{ts}] 第 {attempt:>4} 次 | 名稱狀態：{status_str}", end="")

        if available:
            success, msg = attempt_name_change(target_name, token)
            print(f" → 嘗試改名：{msg}")
            if success:
                print(f"\n[完成] 已成功將名稱改為：{target_name}")
                break
        else:
            print()

        time.sleep(interval)

    print("\n程式結束。")


if __name__ == "__main__":
    main()
