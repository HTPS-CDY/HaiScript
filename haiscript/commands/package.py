"""
HaiScript 包管理器 (hsinser)
从 GitHub 仓库 HTPS-CDY/HSLib 下载和安装扩展包

用法:
  hsinser install <包名> [版本]    安装包（默认最新版本）
  hsinser list                     列出已安装的包
  hsinser remove <包名>            卸载包
  hsinser search <关键词>          搜索可用包
  hsinser info <包名>              显示包详情
  hsinser update [包名|--all]      更新包
  hsinser versions <包名>          列出可用版本
"""

import json
import shutil
import io
import tarfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional

from haiscript.core.constants import CONFIG_DIR
from haiscript.utils.colors import (
    Color,
    print_success, print_error, print_warning, print_info, print_header,
)

# ---- 仓库配置 ----
REPO_OWNER = "HTPS-CDY"
REPO_NAME = "HSLib"
REPO_BRANCH = "main"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GITHUB_RAW = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/raw/{REPO_BRANCH}"
REPO_PACKAGES_DIR = "packages"

# ---- 本地路径 ----
LIB_DIR = Path(__file__).resolve().parent.parent / "lib"
PACKAGES_DB = CONFIG_DIR / "packages.json"


class HsinserError(Exception):
    """包管理器错误"""


class Hsinser:
    """HaiScript 包管理器"""

    def __init__(self):
        self.lib_dir = LIB_DIR
        self.db_path = PACKAGES_DB
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # ==============================================================
    # 元数据
    # ==============================================================
    def _load_db(self) -> Dict:
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return {"packages": {}}

    def _save_db(self, db: Dict):
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise HsinserError(f"保存包元数据失败: {e}")

    # ==============================================================
    # GitHub API
    # ==============================================================
    def _api_get(self, path: str) -> Optional[dict]:
        url = f"{GITHUB_API}/{path}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "HaiScript-hsinser",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise HsinserError(f"GitHub API 请求失败 ({e.code}): {e.reason}")
        except urllib.error.URLError as e:
            raise HsinserError(f"网络请求失败: {e.reason}")

    def _list_repo_dir(self, dir_path: str) -> List[dict]:
        data = self._api_get(f"contents/{dir_path}")
        if data is None:
            return []
        return data if isinstance(data, list) else [data]

    def _download_file(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={
            "User-Agent": "HaiScript-hsinser",
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise HsinserError(f"下载失败 ({e.code}): {e.reason}")
        except urllib.error.URLError as e:
            raise HsinserError(f"下载失败: {e.reason}")

    # ==============================================================
    # 包操作
    # ==============================================================
    def search(self, keyword: str) -> List[Dict]:
        pkgs = self._list_repo_dir(REPO_PACKAGES_DIR)
        results = []
        for p in pkgs:
            if p.get("type") == "dir":
                name = p.get("name", "")
                if keyword.lower() in name.lower():
                    results.append({"name": name})
        return results

    def list_versions(self, package_name: str) -> List[str]:
        items = self._list_repo_dir(f"{REPO_PACKAGES_DIR}/{package_name}")
        versions = []
        for item in items:
            name = item.get("name", "")
            if name.endswith(".tar.gz"):
                versions.append(name[:-7])
        versions.sort(reverse=True)
        return versions

    def get_latest_version(self, package_name: str) -> Optional[str]:
        versions = self.list_versions(package_name)
        return versions[0] if versions else None

    def install(self, package_name: str, version: Optional[str] = None) -> bool:
        # 确定版本
        if version is None:
            version = self.get_latest_version(package_name)
            if version is None:
                print_error(f"包 '{package_name}' 不存在或无可安装版本")
                print_info(f"提示: 仓库可能尚未发布此包")
                return False

        # 检查是否已安装相同版本
        db = self._load_db()
        installed = db["packages"].get(package_name)
        if installed and installed.get("version") == version:
            print_info(f"包 '{package_name}' 版本 {version} 已安装")
            return True

        # 下载
        download_url = (
            f"{GITHUB_RAW}/{REPO_PACKAGES_DIR}/{package_name}/{version}.tar.gz"
        )
        print_info(f"正在下载: {package_name} v{version}")
        print_info(f"  URL: {download_url}")

        try:
            data = self._download_file(download_url)
        except HsinserError as e:
            print_error(f"下载失败: {e}")
            return False

        print_info(f"  下载完成: {len(data):,} 字节")

        # 解压到 lib/<package_name>/
        install_dir = self.lib_dir / package_name
        if install_dir.exists():
            shutil.rmtree(install_dir, ignore_errors=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        print_info(f"正在解压到: {install_dir}")
        file_list = []
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
                for member in tar.getmembers():
                    # 安全检查：防止路径穿越
                    if member.name.startswith('/') or '..' in Path(member.name).parts:
                        print_warning(f"  跳过不安全路径: {member.name}")
                        continue
                    tar.extract(member, install_dir)
                    file_list.append(member.name)
        except tarfile.TarError as e:
            print_error(f"解压失败: {e}")
            return False

        # 更新元数据
        db["packages"][package_name] = {
            "version": version,
            "install_dir": str(install_dir),
            "files": file_list,
        }
        self._save_db(db)

        print_success(f"包 '{package_name}' v{version} 安装成功!")
        print_info(f"  安装目录: {install_dir}")
        print_info(f"  文件数量: {len(file_list)}")
        return True

    def remove(self, package_name: str) -> bool:
        db = self._load_db()
        if package_name not in db["packages"]:
            print_warning(f"包 '{package_name}' 未安装")
            return False

        install_dir = self.lib_dir / package_name
        if install_dir.exists():
            shutil.rmtree(install_dir, ignore_errors=True)

        del db["packages"][package_name]
        self._save_db(db)
        print_success(f"包 '{package_name}' 已卸载")
        return True

    def list_installed(self) -> List[Dict]:
        db = self._load_db()
        result = []
        for name, info in db["packages"].items():
            result.append({
                "name": name,
                "version": info.get("version", "?"),
                "install_dir": info.get("install_dir", str(self.lib_dir / name)),
                "files": info.get("files", []),
            })
        return result

    def info(self, package_name: str) -> Optional[Dict]:
        db = self._load_db()
        installed = db["packages"].get(package_name)

        try:
            versions = self.list_versions(package_name)
        except HsinserError:
            versions = []

        return {
            "name": package_name,
            "installed": installed is not None,
            "installed_version": installed.get("version") if installed else None,
            "available_versions": versions,
            "latest_version": versions[0] if versions else None,
            "install_dir": installed.get("install_dir") if installed else None,
            "file_count": len(installed.get("files", [])) if installed else 0,
        }

    def update(self, package_name: Optional[str] = None) -> bool:
        if package_name in (None, "--all"):
            db = self._load_db()
            if not db["packages"]:
                print_info("没有已安装的包")
                return True
            all_ok = True
            for name in list(db["packages"].keys()):
                print_info(f"更新 {name}...")
                if not self._update_one(name):
                    all_ok = False
            return all_ok
        return self._update_one(package_name)

    def _update_one(self, package_name: str) -> bool:
        latest = self.get_latest_version(package_name)
        if latest is None:
            print_error(f"包 '{package_name}' 不存在或无可用版本")
            return False

        db = self._load_db()
        installed = db["packages"].get(package_name)
        current = installed.get("version") if installed else None

        if current == latest:
            print_info(f"包 '{package_name}' 已是最新版本 ({latest})")
            return True

        print_info(f"更新 {package_name}: {current or '未安装'} -> {latest}")
        return self.install(package_name, latest)

    # ==============================================================
    # 命令入口
    # ==============================================================
    def run_command(self, args: List[str]) -> bool:
        if not args:
            self._print_usage()
            return False

        sub = args[0].lower()
        rest = args[1:]

        commands = {
            'install':   self._cmd_install,
            'list':      self._cmd_list,
            'remove':    self._cmd_remove,
            'uninstall': self._cmd_remove,
            'search':    self._cmd_search,
            'info':      self._cmd_info,
            'update':    self._cmd_update,
            'versions':  self._cmd_versions,
        }

        handler = commands.get(sub)
        if handler is None:
            print_error(f"未知子命令: {sub}")
            self._print_usage()
            return False

        try:
            return handler(rest)
        except HsinserError as e:
            print_error(str(e))
            return False

    def _print_usage(self):
        print_header("hsinser - HaiScript 包管理器")
        print(f"  仓库: https://github.com/{REPO_OWNER}/{REPO_NAME}")
        print()
        print(f"  {Color.BOLD}hsinser install <包名> [版本]{Color.RESET}    安装包")
        print(f"  {Color.BOLD}hsinser list{Color.RESET}                     列出已安装的包")
        print(f"  {Color.BOLD}hsinser remove <包名>{Color.RESET}            卸载包")
        print(f"  {Color.BOLD}hsinser search <关键词>{Color.RESET}          搜索可用包")
        print(f"  {Color.BOLD}hsinser info <包名>{Color.RESET}             显示包详情")
        print(f"  {Color.BOLD}hsinser update [包名|--all]{Color.RESET}     更新包")
        print(f"  {Color.BOLD}hsinser versions <包名>{Color.RESET}          列出可用版本")

    # ---- 子命令处理 ----

    def _cmd_install(self, args: List[str]) -> bool:
        if not args:
            print_error("用法: hsinser install <包名> [版本]")
            return False
        name = args[0]
        version = args[1] if len(args) > 1 else None
        return self.install(name, version)

    def _cmd_list(self, _args: List[str]) -> bool:
        pkgs = self.list_installed()
        if not pkgs:
            print_info("没有已安装的包")
            print_info("使用 'hsinser search <关键词>' 查找可用包")
            return True
        print_header(f"已安装的包 ({len(pkgs)})")
        for p in pkgs:
            print(f"  {Color.BOLD}{p['name']:<20}{Color.RESET} v{p['version']}  ({len(p['files'])} 文件)")
            print(f"    {p['install_dir']}")
        return True

    def _cmd_remove(self, args: List[str]) -> bool:
        if not args:
            print_error("用法: hsinser remove <包名>")
            return False
        return self.remove(args[0])

    def _cmd_search(self, args: List[str]) -> bool:
        keyword = args[0] if args else ""
        if not keyword:
            print_error("用法: hsinser search <关键词>")
            return False
        print_info(f"搜索: '{keyword}'  (仓库: {REPO_OWNER}/{REPO_NAME})")
        results = self.search(keyword)
        if not results:
            print_info("未找到匹配的包")
            print_info("提示: 仓库可能尚未创建或尚未发布任何包")
            return True
        print_header(f"搜索结果 ({len(results)})")
        for r in results:
            print(f"  {Color.BOLD}{r['name']}{Color.RESET}")
        print_info("使用 'hsinser install <包名>' 安装")
        return True

    def _cmd_info(self, args: List[str]) -> bool:
        if not args:
            print_error("用法: hsinser info <包名>")
            return False
        name = args[0]
        info = self.info(name)
        if info is None:
            print_error(f"包 '{name}' 不存在")
            return False
        print_header(f"包详情: {name}")
        if info["installed"]:
            print(f"  状态:        {Color.SUCCESS}已安装{Color.RESET}")
            print(f"  当前版本:    v{info['installed_version']}")
            print(f"  安装目录:    {info['install_dir']}")
            print(f"  文件数量:    {info['file_count']}")
        else:
            print(f"  状态:        {Color.WARNING}未安装{Color.RESET}")
        if info["available_versions"]:
            print(f"  最新版本:    v{info['latest_version']}")
            print(f"  可用版本:    {', '.join(info['available_versions'])}")
        else:
            print(f"  可用版本:    无（仓库可能尚未发布此包）")
        return True

    def _cmd_update(self, args: List[str]) -> bool:
        target = args[0] if args else "--all"
        return self.update(target)

    def _cmd_versions(self, args: List[str]) -> bool:
        if not args:
            print_error("用法: hsinser versions <包名>")
            return False
        name = args[0]
        versions = self.list_versions(name)
        if not versions:
            print_info(f"包 '{name}' 无可用版本（仓库可能尚未发布此包）")
            return True
        print_header(f"包 '{name}' 可用版本")
        for i, v in enumerate(versions):
            tag = f"{Color.SUCCESS}(latest){Color.RESET}" if i == 0 else ""
            print(f"  v{v}  {tag}")
        return True
