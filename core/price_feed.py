"""Live price feed from Binance WebSocket and Coinbase REST API."""
import time
import json
from typing import Optional
import threading
import requests

try:
    import websocket
except ImportError:
    websocket = None

from core.models import LivePrice


class PriceFeed:
    """
    Live BTC price feed with WebSocket primary and REST fallback.

    Primary: Binance WebSocket (BTCUSDT)
    Fallback: Coinbase REST API (BTC-USD)
    """

    def __init__(
        self,
        binance_ws_url: str = "wss://stream.binance.com:9443/ws/btcusdt@trade",
        coinbase_api_url: str = "https://api.coinbase.com/v2/prices/BTC-USD/spot",
        watchdog_timeout: float = 20.0,
        fallback_interval: float = 8.0,
    ):
        """
        Initialize price feed.

        Args:
            binance_ws_url: Binance WebSocket URL
            coinbase_api_url: Coinbase REST API URL
            watchdog_timeout: Seconds before considering WS stale
            fallback_interval: Seconds to wait before using fallback
        """
        self.binance_ws_url = binance_ws_url
        self.coinbase_api_url = coinbase_api_url
        self.watchdog_timeout = watchdog_timeout
        self.fallback_interval = fallback_interval

        self.last_price: Optional[LivePrice] = None
        self.last_tick: float = 0
        self.ws = None
        self.ws_thread = None
        self.running = False

    def fetch_coinbase_price(self) -> Optional[LivePrice]:
        """
        Fetch current price from Coinbase REST API.

        Returns:
            LivePrice object or None if request fails
        """
        try:
            r = requests.get(self.coinbase_api_url, timeout=5)
            r.raise_for_status()
            data = r.json()
            amount = data.get("data", {}).get("amount")
            if amount is not None:
                price = float(amount)
                return LivePrice(
                    price=price,
                    currency="USD",
                    source="Coinbase",
                    timestamp=time.time(),
                )
        except Exception:
            pass
        return None

    def get_latest_price(self) -> Optional[LivePrice]:
        """
        Get the latest price, using fallback if needed.

        Returns:
            LivePrice object or None if no price available
        """
        # Check if WebSocket price is fresh
        if self.last_price and (time.time() - self.last_tick) < self.fallback_interval:
            return self.last_price

        # Try fallback
        fallback_price = self.fetch_coinbase_price()
        if fallback_price:
            self.last_price = fallback_price
            return fallback_price

        return self.last_price

    def _on_message(self, ws, message):
        """WebSocket message handler."""
        try:
            msg = json.loads(message)
            price = float(msg.get("p", 0))
            if price > 0:
                self.last_tick = time.time()
                self.last_price = LivePrice(
                    price=price,
                    currency="USDT",
                    source="Binance",
                    timestamp=self.last_tick,
                )
        except Exception:
            pass

    def _on_error(self, ws, error):
        """WebSocket error handler."""
        pass

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler."""
        if self.running:
            # Attempt reconnect
            time.sleep(1.5)
            if self.running:
                self._connect_ws()

    def _on_open(self, ws):
        """WebSocket open handler."""
        self.last_tick = time.time()

    def _connect_ws(self):
        """Connect to Binance WebSocket."""
        if websocket is None:
            return

        try:
            self.ws = websocket.WebSocketApp(
                self.binance_ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )
            self.ws.run_forever()
        except Exception:
            pass

    def start(self):
        """Start the WebSocket connection in a background thread."""
        if websocket is None or self.running:
            return

        self.running = True
        self.ws_thread = threading.Thread(target=self._connect_ws, daemon=True)
        self.ws_thread.start()

    def stop(self):
        """Stop the WebSocket connection."""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


# Singleton instance for Streamlit caching
_price_feed_instance: Optional[PriceFeed] = None


def get_price_feed() -> PriceFeed:
    """
    Get or create singleton PriceFeed instance.

    Returns:
        PriceFeed instance
    """
    global _price_feed_instance
    if _price_feed_instance is None:
        _price_feed_instance = PriceFeed()
        _price_feed_instance.start()
    return _price_feed_instance
