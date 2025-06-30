#!/usr/bin/env python3
"""
Упрощенный менеджер профилей без зависаний
"""

import os
import time
import json
import threading
from typing import Dict, Tuple, Optional

class SimpleProfileManager:
    """Упрощенный менеджер профилей"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.getcwd()
        self.profiles_state_file = os.path.join(self.base_dir, "profiles_state.json")
        self.lock = threading.Lock()
        
        # Загружаем состояние (без зависаний)
        self.profiles_state = self.load_profiles_state()
        print(f"🔧 Простой менеджер профилей инициализирован")
    
    def load_profiles_state(self) -> Dict:
        """Загрузить состояние профилей"""
        try:
            if os.path.exists(self.profiles_state_file):
                with open(self.profiles_state_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
        except Exception as e:
            print(f"⚠️ Ошибка загрузки состояния: {e}")
        
        return {}
    
    def save_profiles_state(self):
        """Сохранить состояние профилей"""
        try:
            with open(self.profiles_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения состояния: {e}")
    
    def get_available_profile(self, device_type: str = "desktop") -> Tuple[Optional[str], bool]:
        """Получить доступный профиль"""
        
        # Desktop не использует профили
        if device_type == "desktop":
            print("🖥️ Desktop режим: профили не используются")
            return None, False
        
        with self.lock:
            # Ищем существующие свободные профили
            existing_profiles = self.find_existing_profiles()
            
            for profile_path in existing_profiles:
                profile_info = self.profiles_state.get(profile_path, {})
                
                # Если профиль свободен или неизвестен
                if not profile_info.get('in_use', False):
                    print(f"♻️ Переиспользуем профиль: {os.path.basename(profile_path)}")
                    
                    # Помечаем как используемый
                    self.mark_profile_in_use(profile_path, device_type)
                    return profile_path, False
            
            # Создаем новый профиль
            new_profile_path = self.create_new_profile(device_type)
            print(f"🆕 Создан новый профиль: {os.path.basename(new_profile_path)}")
            
            return new_profile_path, True
    
    def find_existing_profiles(self) -> list:
        """Найти существующие профили"""
        import glob
        
        # Ищем только reviews_profile_*
        pattern = os.path.join(self.base_dir, "reviews_profile_*")
        found = glob.glob(pattern)
        
        # Только директории
        return [p for p in found if os.path.isdir(p)]
    
    def create_new_profile(self, device_type: str) -> str:
        """Создать новый профиль"""
        timestamp = int(time.time() * 1000)
        profile_name = f"reviews_profile_{timestamp}"
        profile_path = os.path.join(self.base_dir, profile_name)
        
        # Создаем директорию
        os.makedirs(profile_path, exist_ok=True)
        
        # Помечаем как используемый
        self.mark_profile_in_use(profile_path, device_type)
        
        return profile_path
    
    def mark_profile_in_use(self, profile_path: str, device_type: str):
        """Пометить профиль как используемый"""
        self.profiles_state[profile_path] = {
            'in_use': True,
            'pid': os.getpid(),
            'device_type': device_type,
            'last_used': time.time(),
            'created': time.time()
        }
        self.save_profiles_state()
    
    def release_profile(self, profile_path: str):
        """Освободить профиль"""
        with self.lock:
            if profile_path in self.profiles_state:
                self.profiles_state[profile_path]['in_use'] = False
                self.profiles_state[profile_path]['pid'] = None
                self.profiles_state[profile_path]['last_used'] = time.time()
                self.save_profiles_state()
                print(f"✅ Профиль освобожден: {os.path.basename(profile_path)}")
    
    def get_stats(self) -> Dict:
        """Получить статистику профилей"""
        existing_profiles = self.find_existing_profiles()
        
        stats = {
            'total_profiles': len(existing_profiles),
            'in_use': 0,
            'available': 0,
            'profiles': []
        }
        
        for profile_path in existing_profiles:
            profile_info = self.profiles_state.get(profile_path, {})
            is_in_use = profile_info.get('in_use', False)
            
            if is_in_use:
                stats['in_use'] += 1
            else:
                stats['available'] += 1
            
            stats['profiles'].append({
                'path': profile_path,
                'name': os.path.basename(profile_path),
                'in_use': is_in_use,
                'device_type': profile_info.get('device_type', 'unknown'),
                'last_used': profile_info.get('last_used', 0)
            })
        
        return stats
    
    def print_stats(self):
        """Вывести статистику профилей"""
        stats = self.get_stats()
        
        print(f"\n📊 Статистика профилей:")
        print(f"   📁 Всего профилей: {stats['total_profiles']}")
        print(f"   🔴 Используется: {stats['in_use']}")
        print(f"   🟢 Доступно: {stats['available']}")
        
        if stats['profiles']:
            print(f"\n📋 Список профилей:")
            for profile in stats['profiles']:
                status = "🔴 используется" if profile['in_use'] else "🟢 доступен"
                device = profile['device_type']
                print(f"   {status} | {device} | {profile['name']}")

if __name__ == "__main__":
    # Тест простого менеджера
    print("🧪 ТЕСТ ПРОСТОГО МЕНЕДЖЕРА ПРОФИЛЕЙ")
    print("=" * 45)
    
    manager = SimpleProfileManager()
    
    # Показываем статистику
    manager.print_stats()
    
    # Тест mobile профиля
    print(f"\n📱 Тест mobile профиля:")
    profile_path, is_new = manager.get_available_profile("mobile")
    
    if profile_path:
        print(f"✅ Получен профиль: {os.path.basename(profile_path)}")
        print(f"   🆕 Новый: {is_new}")
        print(f"   📁 Существует: {os.path.exists(profile_path)}")
        
        # Показываем статистику после создания
        manager.print_stats()
        
        # Освобождаем профиль
        manager.release_profile(profile_path)
        print(f"\n🔓 Профиль освобожден")
        
        # Показываем финальную статистику
        manager.print_stats()
    else:
        print(f"❌ Профиль не получен")
    
    print(f"\n👋 Тест завершен") 