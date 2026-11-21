import platform


def is_debian_like() -> bool:
    try:
        os_release = platform.freedesktop_os_release()
    except Exception:
        return False

    id = os_release.get("ID", "")
    id_like = os_release.get("ID_LIKE", "").split()

    return id == "debian" or "debian" in id_like
