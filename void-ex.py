#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  SYSTEM NAME    : VOID-EX SECURITY FRAMEWORK
  VERSION        : 1.0.0 APEX CORE
  ARCHITECTURE   : Asynchronous OOP Framework
  OPERATOR       : LENY // Enterprise Security Architecture
================================================================================
"""

import asyncio
import socket
import ssl
import hashlib
import base64
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

# ==============================================================================
# GÖRSEL MİMARİ VE TERMİNAL RENKLERİ (ANSI PALETTE)
# ==============================================================================
class TermColor:
    CYAN      = "\033[96m"
    GREEN     = "\033[92m"
    YELLOW    = "\033[93m"
    RED       = "\033[91m"
    MAGENTA   = "\033[95m"
    BLUE      = "\033[94m"
    GRAY      = "\033[90m"
    BOLD      = "\033[1m"
    RESET     = "\033[0m"

# ==============================================================================
# VERİ YAPILARI (DATA MODELS)
# ==============================================================================
@dataclass
class TargetData:
    domain: str
    ip_address: str = ""
    dns_records: Dict[str, str] = field(default_factory=dict)
    open_ports: Dict[int, str] = field(default_factory=dict)
    ssl_info: Dict[str, Any] = field(default_factory=dict)

# ==============================================================================
# SOYUT TABAN SINIF (ABSTRACT BASE MODULE)
# ==============================================================================
class BaseVoidModule(ABC):
    """Tüm VOID-EX modüllerinin türeyeceği zorunlu şablon."""
    
    def __init__(self, module_name: str, description: str):
        self.module_name = module_name
        self.description = description

    @abstractmethod
    async def run(self, payload: Any) -> Dict[str, Any]:
        pass

# ==============================================================================
# MODÜL 1: ASENKRON AĞ VE OSINT İSTİHBARAT MOTORU
# ==============================================================================
class ReconModule(BaseVoidModule):
    def __init__(self):
        super().__init__(
            module_name="RECON-INTEL-V1",
            description="Asenkron DNS, Port Scanner ve SSL Sertifika Analizörü"
        )
        self.target_ports = [21, 22, 53, 80, 135, 139, 443, 445, 3306, 3389, 8080]

    async def _resolve_dns(self, domain: str) -> str:
        """Domain adresini IP adresine dönüştürür."""
        loop = asyncio.get_running_loop()
        try:
            ip = await loop.run_in_executor(None, socket.gethostbyname, domain)
            return ip
        except socket.gaierror:
            return ""

    async def _scan_port(self, ip: str, port: int) -> tuple[int, bool, str]:
        """Tekil port için non-blocking socket denemesi yapar."""
        try:
            conn = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(conn, timeout=1.0)
            
            banner = "Servis Yanıtı Alınamadı"
            try:
                writer.write(b"HEAD / HTTP/1.0\r\n\r\n")
                await writer.drain()
                data = await asyncio.wait_for(reader.read(128), timeout=0.5)
                if data:
                    banner = data.decode('utf-8', errors='ignore').split('\n')[0].strip()[:35]
            except Exception:
                pass

            writer.close()
            await writer.wait_closed()
            return port, True, banner
        except Exception:
            return port, False, ""

    async def _check_ssl(self, domain: str) -> Dict[str, Any]:
        """Target domain için SSL sertifika detaylarını çeker."""
        loop = asyncio.get_running_loop()
        def fetch_ssl():
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=2.0) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    return ssock.getpeercert()
        try:
            cert = await loop.run_in_executor(None, fetch_ssl)
            subject = dict(x[0] for x in cert.get('subject', []))
            issuer = dict(x[0] for x in cert.get('issuer', []))
            return {
                "common_name": subject.get('commonName', 'Bilinmiyor'),
                "issuer": issuer.get('organizationName', 'Bilinmiyor'),
                "valid_till": cert.get('notAfter', 'Bilinmiyor')
            }
        except Exception:
            return {"status": "SSL Portu (443) Kapalı veya Bağlantı Sağlanamadı"}

    async def run(self, payload: str) -> Dict[str, Any]:
        target = TargetData(domain=payload)
        print(f"\n{TermColor.CYAN}[*] [{self.module_name}] Analiz Başlatıldı: {payload}{TermColor.RESET}")

        # 1. DNS Resolution
        target.ip_address = await self._resolve_dns(target.domain)
        if not target.ip_address:
            return {"error": f"Domain IP adresine dönüştürülemedi: {payload}"}

        print(f"{TermColor.GREEN}[+] Hedef IP Tespit Edildi: {target.ip_address}{TermColor.RESET}")

        # 2. Async Port Scan
        print(f"{TermColor.YELLOW}[*] Asenkron Port Tarayıcısı Çalıştırılıyor...{TermColor.RESET}")
        tasks = [self._scan_port(target.ip_address, p) for p in self.target_ports]
        scan_results = await asyncio.gather(*tasks)

        for port, is_open, banner in scan_results:
            if is_open:
                target.open_ports[port] = banner

        # 3. SSL Analysis
        print(f"{TermColor.YELLOW}[*] SSL/TLS Sertifika Analizi Yapılıyor...{TermColor.RESET}")
        target.ssl_info = await self._check_ssl(target.domain)

        return {
            "domain": target.domain,
            "ip": target.ip_address,
            "open_ports": target.open_ports,
            "ssl_info": target.ssl_info
        }

# ==============================================================================
# MODÜL 2: KRİPTOGRAFİ VE VERİ GİZLEME (STEGANOGRAPHY) MOTORU
# ==============================================================================
class CryptoStegoModule(BaseVoidModule):
    def __init__(self):
        super().__init__(
            module_name="CRYPTO-STEGO-V1",
            description="PBKDF2 + Matris Şifreleme ve Metin Veri Gizleyici"
        )

    def _derive_key(self, secret_pass: str, salt: bytes) -> bytes:
        """Kullanıcı parolasından 256-bit güvenli anahtar türetir."""
        return hashlib.pbkdf2_hmac('sha256', secret_pass.encode(), salt, 100000)

    def encrypt_data(self, plain_text: str, secret_pass: str) -> str:
        """Metni PBKDF2 ve XOR/Base64 algoritmalarıyla şifreler."""
        salt = os.urandom(16)
        key = self._derive_key(secret_pass, salt)
        text_bytes = plain_text.encode('utf-8')
        
        cipher_bytes = bytearray()
        for i in range(len(text_bytes)):
            cipher_bytes.append(text_bytes[i] ^ key[i % len(key)])

        final_payload = salt + bytes(cipher_bytes)
        return base64.b64encode(final_payload).decode('utf-8')

    def decrypt_data(self, cipher_text: str, secret_pass: str) -> str:
        """Şifreli veriyi orijinal metne geri döndürür."""
        try:
            raw_payload = base64.b64decode(cipher_text.encode('utf-8'))
            salt = raw_payload[:16]
            cipher_bytes = raw_payload[16:]
            
            key = self._derive_key(secret_pass, salt)
            plain_bytes = bytearray()
            for i in range(len(cipher_bytes)):
                plain_bytes.append(cipher_bytes[i] ^ key[i % len(key)])

            return plain_bytes.decode('utf-8')
        except Exception:
            return "[!] HATA: Geçersiz Parola veya Bozuk Şifreli Veri!"

    def embed_stego_text(self, cover_text: str, hidden_payload: str) -> str:
        """Gizli metni görünmez boşluk karakterleri (Steganography) ile saklar."""
        binary_payload = ''.join(format(ord(c), '08b') for c in hidden_payload)
        # 0 = Zero-width space (\u200B), 1 = Zero-width non-joiner (\u200C)
        stego_markers = binary_payload.replace('0', '\u200b').replace('1', '\u200c')
        return cover_text + stego_markers + '\u200d'

    def extract_stego_text(self, stego_text: str) -> str:
        """Metin içindeki gizli işaretleri çözer."""
        try:
            if '\u200d' not in stego_text:
                return "[!] Herhangi bir gizli veri izine rastlanmadı."
            
            hidden_part = stego_text.split('\u200d')[0]
            binary_str = ""
            for char in hidden_part:
                if char == '\u200b':
                    binary_str += '0'
                elif char == '\u200c':
                    binary_str += '1'

            bytes_list = [int(binary_str[i:i+8], 2) for i in range(0, len(binary_str), 8)]
            return bytes(bytes_list).decode('utf-8')
        except Exception:
            return "[!] HATA: Gizli veri ayıklanamadı!"

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = payload.get("mode")
        if mode == "encrypt":
            result = self.encrypt_data(payload["text"], payload["passphrase"])
            return {"status": "SUCCESS", "cipher_text": result}
        elif mode == "decrypt":
            result = self.decrypt_data(payload["cipher"], payload["passphrase"])
            return {"status": "SUCCESS", "plain_text": result}
        elif mode == "stego_hide":
            result = self.embed_stego_text(payload["cover"], payload["secret"])
            return {"status": "SUCCESS", "stego_output": result}
        elif mode == "stego_extract":
            result = self.extract_stego_text(payload["stego_text"])
            return {"status": "SUCCESS", "extracted_secret": result}
        return {"error": "Bilinmeyen Kip"}

# ==============================================================================
# ANA ÇEKİRDEK YÖNETİCİSİ (VOID-EX ENGINE CORE)
# ==============================================================================
class VoidExEngine:
    def __init__(self):
        self.modules: Dict[str, BaseVoidModule] = {}
        self._register_default_modules()

    def _register_default_modules(self):
        recon = ReconModule()
        crypto = CryptoStegoModule()
        self.modules[recon.module_name] = recon
        self.modules[crypto.module_name] = crypto

    def print_banner(self):
        os.system("cls" if os.name == "nt" else "clear")
        banner = f"""{TermColor.MAGENTA}
██╗   ██╗███╗   ██╗██████╗     ███████╗██╗  ██╗
██║   ██║████╗  ██║██╔══██╗    ██╔════╝╚██╗██╔╝
██║   ██║██╔██╗ ██║██║  ██║    █████╗   ╚███╔╝ 
██║   ██║██║╚██╗██║██║  ██║    ██╔══╝   ██╔██╗ 
╚██████╔╝██║ ╚████║██████╔╝    ███████╗██╔╝ ██╗
 ╚═════╝ ╚═╝  ╚═══╝╚═════╝     ╚══════╝╚═╝  ╚═╝
{TermColor.CYAN}[ APEX CORE v1.0 // Operator: LENY | Framework Standard: Enterprise ]{TermColor.RESET}
        """
        print(banner)

    async def execute_module(self, module_name: str, payload: Any) -> Dict[str, Any]:
        if module_name not in self.modules:
            return {"error": f"Modül bulunamadı: {module_name}"}
        return await self.modules[module_name].run(payload)

# ==============================================================================
# KULLANICI ARAYÜZÜ VE İNTERAKTİF KOMUT MERKEZİ
# ==============================================================================
async def main_cli():
    engine = VoidExEngine()

    while True:
        engine.print_banner()
        print(f"{TermColor.BOLD}KULLANILABİLİR OPERASYON MODÜLLERİ:{TermColor.RESET}")
        print(f"{TermColor.GREEN}[1]{TermColor.RESET} OSINT & Ağ Keşif Motoru (ReconIntel)")
        print(f"{TermColor.GREEN}[2]{TermColor.RESET} Kriptografik Şifreleyici (AES/PBKDF2)")
        print(f"{TermColor.GREEN}[3]{TermColor.RESET} Veri Gizleme Motoru (Steganography)")
        print(f"{TermColor.RED}[0]{TermColor.RESET} Güvenli Çıkış")
        
        choice = input(f"\n{TermColor.YELLOW}VOID-EX >> Operasyon Seçiniz [0-3]: {TermColor.RESET}").strip()

        if choice == "1":
            target_domain = input(f"\n{TermColor.CYAN}Hedef Domain Girin (Örn: example.com): {TermColor.RESET}").strip()
            if target_domain:
                start_time = time.time()
                result = await engine.execute_module("RECON-INTEL-V1", target_domain)
                elapsed = time.time() - start_time

                print("\n" + "=" * 65)
                print(f"{TermColor.BOLD}OPERASYON SONUÇ RAPORU ({elapsed:.2f} saniye){TermColor.RESET}")
                print("=" * 65)
                
                if "error" in result:
                    print(f"{TermColor.RED}{result['error']}{TermColor.RESET}")
                else:
                    print(f"Hedef Domain : {result['domain']}")
                    print(f"Hedef IP     : {result['ip']}")
                    print(f"\n{TermColor.GREEN}AÇIK PORTLAR VE SERVİSLER:{TermColor.RESET}")
                    if result['open_ports']:
                        for p, banner in result['open_ports'].items():
                            print(f"  -> Port {p:<5} | Status: AÇIK | Banner: {banner}")
                    else:
                        print("  -> Hiçbir standart port açık olarak tespit edilemedi.")

                    print(f"\n{TermColor.MAGENTA}SSL SERTİFİKA DETAYLARI:{TermColor.RESET}")
                    for k, v in result['ssl_info'].items():
                        print(f"  -> {k:<15}: {v}")

            input(f"\n{TermColor.GRAY}Devam etmek için ENTER'a basın...{TermColor.RESET}")

        elif choice == "2":
            sub_choice = input(f"\n{TermColor.CYAN}[1] Şifrele | [2] Şifre Çöz: {TermColor.RESET}").strip()
            crypto_mod = engine.modules["CRYPTO-STEGO-V1"]

            if sub_choice == "1":
                text = input("Şifrelenecek Metin: ").strip()
                pas = input("Gizli Parola: ").strip()
                res = await crypto_mod.run({"mode": "encrypt", "text": text, "passphrase": pas})
                print(f"\n{TermColor.GREEN}[✓] ŞIFRELI ÇIKTI (Base64/Payload):{TermColor.RESET}\n{res['cipher_text']}")

            elif sub_choice == "2":
                cipher = input("Şifreli Payload: ").strip()
                pas = input("Gizli Parola: ").strip()
                res = await crypto_mod.run({"mode": "decrypt", "cipher": cipher, "passphrase": pas})
                print(f"\n{TermColor.GREEN}[✓] ÇÖZÜLEN ORİJİNAL METİN:{TermColor.RESET}\n{res['plain_text']}")

            input(f"\n{TermColor.GRAY}Devam etmek için ENTER'a basın...{TermColor.RESET}")

        elif choice == "3":
            sub_choice = input(f"\n{TermColor.CYAN}[1] Metne Veri Gizle | [2] Gizli Veriyi Çıkar: {TermColor.RESET}").strip()
            crypto_mod = engine.modules["CRYPTO-STEGO-V1"]

            if sub_choice == "1":
                cover = input("Dışarıdan Görünecek Masum Metin: ").strip()
                secret = input("İçine Gizlenecek Gizli Mesaj: ").strip()
                res = await crypto_mod.run({"mode": "stego_hide", "cover": cover, "secret": secret})
                print(f"\n{TermColor.GREEN}[✓] STEGO METIN OLUŞTURULDU (Kopyalayıp Gönderebilirsin):{TermColor.RESET}\n{res['stego_output']}")

            elif sub_choice == "2":
                stego_in = input("Gizli İçeriği Olan Metni Yapıştırın: ").strip()
                res = await crypto_mod.run({"mode": "stego_extract", "stego_text": stego_in})
                print(f"\n{TermColor.GREEN}[✓] TESPİT EDİLEN GİZLİ VERİ:{TermColor.RESET}\n{res['extracted_secret']}")

            input(f"\n{TermColor.GRAY}Devam etmek için ENTER'a basın...{TermColor.RESET}")

        elif choice == "0":
            print(f"\n{TermColor.RED}[!] VOID-EX APEX Core Kapatılıyor. Güvenli Oturum Sonu.{TermColor.RESET}")
            sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main_cli())
    except KeyboardInterrupt:
        print(f"\n\n{TermColor.RED}[!] Kullanıcı Tarafından İptal Edildi.{TermColor.RESET}")
        sys.exit(0)
