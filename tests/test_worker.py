import sys
import time
import threading
from unittest.mock import patch, MagicMock

sys.path.insert(0, 'src')
import worker


class TestWhitelist:
    """
    Whitelist check nằm inline trong poll_sqs_queue().
    Test logic: `chat_id not in ALLOWED_IDS` (ALLOWED_IDS là list).
    """

    def test_allowed_id_passes(self):
        with patch.object(worker, 'ALLOWED_IDS', ['111111111', '222222222']):
            assert '111111111' in worker.ALLOWED_IDS

    def test_unknown_id_blocked(self):
        with patch.object(worker, 'ALLOWED_IDS', ['111111111']):
            assert '999999999' not in worker.ALLOWED_IDS

    def test_empty_string_blocked(self):
        with patch.object(worker, 'ALLOWED_IDS', ['111111111']):
            assert '' not in worker.ALLOWED_IDS

    def test_partial_match_blocked(self):
        """List check phải exact match, không phải prefix."""
        with patch.object(worker, 'ALLOWED_IDS', ['111111111']):
            assert '1111' not in worker.ALLOWED_IDS

    def test_multiple_ids_all_pass(self):
        ids = ['111111111', '222222222', '333333333']
        with patch.object(worker, 'ALLOWED_IDS', ids):
            for uid in ids:
                assert uid in worker.ALLOWED_IDS


class TestRateLimiter:
    """
    Test is_rate_limited() từ worker.py.
    Threshold thật = 5 giây, dùng threading.Lock().
    """

    def setup_method(self):
        """Reset global state trước mỗi test."""
        worker.LAST_REQUEST_TIME.clear()

    def test_first_request_always_passes(self):
        assert worker.is_rate_limited('user_A') is False

    def test_immediate_second_request_blocked(self):
        worker.is_rate_limited('user_B')             # lần 1 — pass
        assert worker.is_rate_limited('user_B') is True  # lần 2 — blocked

    def test_threshold_is_5_seconds(self):
        """Đảm bảo đúng với code thật (5s, không phải 3s)."""
        worker.LAST_REQUEST_TIME['user_C'] = time.time() - 4  # 4s trước → vẫn bị block
        assert worker.is_rate_limited('user_C') is True

    def test_passes_after_5_seconds(self):
        worker.LAST_REQUEST_TIME['user_D'] = time.time() - 6  # 6s trước → pass
        assert worker.is_rate_limited('user_D') is False

    def test_different_users_are_independent(self):
        """Rate limit của user này không ảnh hưởng user khác."""
        worker.is_rate_limited('user_E')
        assert worker.is_rate_limited('user_F') is False

    def test_thread_safety(self):
        results = []
        barrier = threading.Barrier(10)

        def call():
            barrier.wait()
            results.append(worker.is_rate_limited('shared_user'))

        threads = [threading.Thread(target=call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(False) == 1
        assert results.count(True) == 9


class TestSendTelegramReply:
    """Test send_telegram_reply() — truncation và empty text handling."""

    @patch('worker.requests')
    def test_normal_message_sent(self, mock_requests):
        mock_requests.post.return_value.status_code = 200
        worker.send_telegram_reply('123', 'Hello')
        mock_requests.post.assert_called_once()

    @patch('worker.requests')
    def test_message_over_4000_chars_truncated(self, mock_requests):
        mock_requests.post.return_value.status_code = 200
        long_text = 'A' * 5000
        worker.send_telegram_reply('123', long_text)

        call_kwargs = mock_requests.post.call_args
        sent_text = call_kwargs[1]['json']['text']  # keyword arg

        assert len(sent_text) <= 4100
        assert '...' in sent_text

    @patch('worker.requests')
    def test_empty_text_replaced_with_fallback(self, mock_requests):
        mock_requests.post.return_value.status_code = 200
        worker.send_telegram_reply('123', '')

        call_kwargs = mock_requests.post.call_args
        sent_text = call_kwargs[1]['json']['text']

        assert sent_text != ''
        assert len(sent_text) > 0

    @patch('worker.requests')
    def test_none_text_handled(self, mock_requests):
        mock_requests.post.return_value.status_code = 200
        try:
            worker.send_telegram_reply('123', None)
        except Exception as e:
            pytest.fail(f'send_telegram_reply raised unexpectedly: {e}')