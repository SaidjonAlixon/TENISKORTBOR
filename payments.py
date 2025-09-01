"""
To'lov tizimlari integratsiyasi
"""

import aiohttp
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple
from config import Config
from utils import generate_payment_signature, verify_payment_signature

class PaymentError(Exception):
    """To'lov xatosi"""
    pass

class PaymentProvider:
    """Asosiy to'lov provider klassi"""
    
    def __init__(self):
        self.session = None
    
    async def create_session(self):
        """HTTP session yaratish"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """HTTP session yopish"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def create_payment(self, amount: float, order_id: str, 
                           return_url: str = None) -> Dict:
        """To'lov yaratish (abstract method)"""
        raise NotImplementedError
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """To'lov holatini tekshirish (abstract method)"""
        raise NotImplementedError
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """To'lovni bekor qilish (abstract method)"""
        raise NotImplementedError

class PaymeProvider(PaymentProvider):
    """Payme to'lov tizimi"""
    
    def __init__(self):
        super().__init__()
        self.merchant_id = Config.PAYME_MERCHANT_ID
        self.secret_key = Config.PAYME_SECRET_KEY
        self.test_mode = Config.PAYME_TEST_MODE
        
        if self.test_mode:
            self.base_url = "https://checkout.test.paycom.uz/api"
        else:
            self.base_url = "https://checkout.paycom.uz/api"
    
    def _generate_auth_header(self) -> str:
        """Authorization header yaratish"""
        import base64
        auth_string = f"Paycom:{self.secret_key}"
        return base64.b64encode(auth_string.encode()).decode()
    
    async def create_payment(self, amount: float, order_id: str, 
                           return_url: str = None) -> Dict:
        """Payme to'lov yaratish - VAQTINCHA QO'LDA TASDIQLASH"""
        await self.create_session()
        
        # VAQTINCHA: Haqiqiy to'lov URL o'rniga mock
        return {
            'payment_id': f'payme_manual_{order_id}',
            'payment_url': f'https://test.payme.uz/manual/{order_id}',
            'amount': amount,
            'status': 'pending',
            'method': 'payme'
        }
    
    def _generate_payment_link(self, amount: int, order_id: str) -> str:
        """To'lov havolasini yaratish"""
        import base64
        
        params = {
            'm': self.merchant_id,
            'ac.order_id': order_id,
            'a': amount
        }
        
        # Parametrlarni base64 ga encode qilish
        params_json = json.dumps(params)
        encoded_params = base64.b64encode(params_json.encode()).decode()
        
        return encoded_params
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """Payme to'lov holatini tekshirish"""
        await self.create_session()
        
        headers = {
            'Authorization': f'Basic {self._generate_auth_header()}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'method': 'GetStatement',
            'params': {
                'from': int((datetime.now().timestamp() - 86400) * 1000),  # 24 soat oldin
                'to': int(datetime.now().timestamp() * 1000)
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                
                if 'result' in data:
                    # To'lov ma'lumotlarini qidirish
                    for transaction in data['result']['transactions']:
                        if transaction.get('account', {}).get('order_id') == payment_id:
                            state = transaction.get('state')
                            if state == 2:  # To'langan
                                return {
                                    'status': 'paid',
                                    'transaction_id': transaction.get('id'),
                                    'amount': transaction.get('amount', 0) / 100
                                }
                            elif state == -1:  # Bekor qilingan
                                return {
                                    'status': 'cancelled',
                                    'transaction_id': transaction.get('id')
                                }
                            else:
                                return {
                                    'status': 'pending',
                                    'transaction_id': transaction.get('id')
                                }
                
                return {'status': 'not_found'}
                
        except Exception as e:
            raise PaymentError(f"Payme API xatosi: {str(e)}")

class ClickProvider(PaymentProvider):
    """Click to'lov tizimi"""
    
    def __init__(self):
        super().__init__()
        self.merchant_id = Config.CLICK_MERCHANT_ID
        self.service_id = Config.CLICK_SERVICE_ID
        self.secret_key = Config.CLICK_SECRET_KEY
        self.test_mode = Config.CLICK_TEST_MODE
        
        if self.test_mode:
            self.base_url = "https://api.click.uz/v2/merchant"
        else:
            self.base_url = "https://api.click.uz/v2/merchant"
    
    async def create_payment(self, amount: float, order_id: str, 
                           return_url: str = None) -> Dict:
        """Click to'lov yaratish - VAQTINCHA QO'LDA TASDIQLASH"""
        await self.create_session()
        
        # VAQTINCHA: Haqiqiy API o'rniga mock
        return {
            'payment_id': f'click_manual_{order_id}',
            'payment_url': f'https://test.click.uz/manual/{order_id}',
            'amount': amount,
            'status': 'pending',
            'method': 'click'
        }
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """Click to'lov holatini tekshirish"""
        await self.create_session()
        
        check_data = {
            'service_id': self.service_id,
            'merchant_id': self.merchant_id,
            'invoice_id': payment_id
        }
        
        # Imzo yaratish
        sign_string = f"{check_data['service_id']}{check_data['merchant_id']}{check_data['invoice_id']}{self.secret_key}"
        check_data['sign'] = hashlib.md5(sign_string.encode()).hexdigest()
        
        try:
            async with self.session.post(
                f"{self.base_url}/invoice/status",
                json=check_data
            ) as response:
                data = await response.json()
                
                if data.get('error_code') == 0:
                    status_code = data.get('invoice_status')
                    if status_code == 2:  # To'langan
                        return {
                            'status': 'paid',
                            'transaction_id': data.get('payment_id'),
                            'amount': data.get('amount', 0) / 100
                        }
                    elif status_code == -1:  # Bekor qilingan
                        return {
                            'status': 'cancelled',
                            'transaction_id': data.get('payment_id')
                        }
                    else:
                        return {
                            'status': 'pending',
                            'transaction_id': data.get('payment_id')
                        }
                else:
                    return {'status': 'not_found'}
                    
        except Exception as e:
            raise PaymentError(f"Click API xatosi: {str(e)}")

class UzumPayProvider(PaymentProvider):
    """Uzum Pay to'lov tizimi"""
    
    def __init__(self):
        super().__init__()
        self.merchant_id = Config.UZUM_MERCHANT_ID
        self.secret_key = Config.UZUM_SECRET_KEY
        self.test_mode = Config.UZUM_TEST_MODE
        
        if self.test_mode:
            self.base_url = "https://api.test.uzum.uz/v1"
        else:
            self.base_url = "https://api.uzum.uz/v1"
    
    async def create_payment(self, amount: float, order_id: str, 
                           return_url: str = None) -> Dict:
        """Uzum Pay to'lov yaratish - VAQTINCHA QO'LDA TASDIQLASH"""
        return {
            'payment_id': f"uzum_manual_{order_id}",
            'payment_url': f"https://test.uzum.uz/manual/{order_id}",
            'amount': amount,
            'status': 'pending',
            'method': 'uzum'
        }
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """Uzum Pay to'lov holatini tekshirish"""
        # Mock implementation
        return {'status': 'pending'}

class PaymentManager:
    """To'lov menejeri"""
    
    def __init__(self):
        self.providers = {
            'payme': PaymeProvider(),
            'click': ClickProvider(),
            'uzum': UzumPayProvider()
        }
    
    async def create_payment(self, method: str, amount: float, 
                           order_id: str, return_url: str = None) -> Dict:
        """To'lov yaratish"""
        if method not in self.providers:
            raise PaymentError(f"Noto'g'ri to'lov usuli: {method}")
        
        provider = self.providers[method]
        return await provider.create_payment(amount, order_id, return_url)
    
    async def check_payment_status(self, method: str, payment_id: str) -> Dict:
        """To'lov holatini tekshirish"""
        if method not in self.providers:
            raise PaymentError(f"Noto'g'ri to'lov usuli: {method}")
        
        provider = self.providers[method]
        return await provider.check_payment_status(payment_id)
    
    async def cancel_payment(self, method: str, payment_id: str) -> bool:
        """To'lovni bekor qilish"""
        if method not in self.providers:
            raise PaymentError(f"Noto'g'ri to'lov usuli: {method}")
        
        provider = self.providers[method]
        return await provider.cancel_payment(payment_id)
    
    async def close_all_sessions(self):
        """Barcha sessiyalarni yopish"""
        for provider in self.providers.values():
            await provider.close_session()

# Webhook handlers
async def handle_payme_webhook(data: Dict) -> Dict:
    """Payme webhook ishlov berish"""
    method = data.get('method')
    
    if method == 'CheckPerformTransaction':
        # To'lov imkoniyatini tekshirish
        account = data.get('params', {}).get('account', {})
        order_id = account.get('order_id')
        
        # Bu yerda order_id ni database da tekshirish kerak
        # Hozircha mock response
        return {
            'result': {
                'allow': True
            }
        }
    
    elif method == 'CreateTransaction':
        # Tranzaksiya yaratish
        return {
            'result': {
                'create_time': int(datetime.now().timestamp() * 1000),
                'transaction': data.get('params', {}).get('id'),
                'state': 1
            }
        }
    
    elif method == 'PerformTransaction':
        # To'lovni amalga oshirish
        return {
            'result': {
                'perform_time': int(datetime.now().timestamp() * 1000),
                'transaction': data.get('params', {}).get('id'),
                'state': 2
            }
        }
    
    elif method == 'CancelTransaction':
        # To'lovni bekor qilish
        return {
            'result': {
                'cancel_time': int(datetime.now().timestamp() * 1000),
                'transaction': data.get('params', {}).get('id'),
                'state': -1
            }
        }
    
    elif method == 'CheckTransaction':
        # Tranzaksiya holatini tekshirish
        return {
            'result': {
                'create_time': int(datetime.now().timestamp() * 1000),
                'perform_time': int(datetime.now().timestamp() * 1000),
                'cancel_time': 0,
                'transaction': data.get('params', {}).get('id'),
                'state': 2,
                'reason': None
            }
        }
    
    return {'error': {'code': -32400, 'message': 'Noto\'g\'ri method'}}

async def handle_click_webhook(data: Dict) -> Dict:
    """Click webhook ishlov berish"""
    # Click webhook parametrlari
    click_trans_id = data.get('click_trans_id')
    service_id = data.get('service_id')
    merchant_trans_id = data.get('merchant_trans_id')
    amount = data.get('amount')
    action = data.get('action')
    error = data.get('error')
    sign_time = data.get('sign_time')
    sign_string = data.get('sign_string')
    
    # Imzoni tekshirish
    expected_sign = hashlib.md5(
        f"{click_trans_id}{service_id}{Config.CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}".encode()
    ).hexdigest()
    
    if sign_string != expected_sign:
        return {
            'error': -1,
            'error_note': 'Noto\'g\'ri imzo'
        }
    
    if action == 0:  # Prepare
        # To'lovni tayyorlash
        return {
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_prepare_id': int(datetime.now().timestamp()),
            'error': 0,
            'error_note': 'Success'
        }
    
    elif action == 1:  # Complete
        # To'lovni yakunlash
        return {
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_confirm_id': int(datetime.now().timestamp()),
            'error': 0,
            'error_note': 'Success'
        }
    
    return {
        'error': -9,
        'error_note': 'Noto\'g\'ri action'
    }

# Global payment manager
payment_manager = PaymentManager()
