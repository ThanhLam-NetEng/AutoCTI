import sys
import json
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch


# ── BƯỚC 1: Tạo fake base classes thật (phải là class, không phải MagicMock) ──

class _FakeBaseChatMessageHistory:
    """Stub đủ để TimeSeriesDynamoDBHistory kế thừa."""
    pass

class _FakeBaseMessage:
    pass

# ── BƯỚC 2: Inject vào sys.modules trước khi import custom_memory ──────────────

# Xóa cache cũ nếu conftest đã mock rồi
for mod in ['langchain_core', 'langchain_core.chat_history',
            'langchain_core.messages', 'custom_memory']:
    sys.modules.pop(mod, None)

_mock_chat_history_mod = MagicMock()
_mock_chat_history_mod.BaseChatMessageHistory = _FakeBaseChatMessageHistory
sys.modules['langchain_core.chat_history'] = _mock_chat_history_mod

_mock_messages_mod = MagicMock()
_mock_messages_mod.BaseMessage = _FakeBaseMessage
# message_to_dict / messages_from_dict cần mock riêng trong từng test
sys.modules['langchain_core.messages'] = _mock_messages_mod

_mock_langchain_core = MagicMock()
_mock_langchain_core.chat_history = _mock_chat_history_mod
_mock_langchain_core.messages = _mock_messages_mod
sys.modules['langchain_core'] = _mock_langchain_core

# ── BƯỚC 3: Bây giờ mới import class thật ──────────────────────────────────────
sys.path.insert(0, 'src')
import custom_memory                              # module thật
from custom_memory import TimeSeriesDynamoDBHistory  # class thật


# ─────────────────────────────────────────────────────────────────────────────
class TestTimeSeriesDynamoDBHistory:

    def _make_history(self, mock_table):
        with patch.object(custom_memory, '_dynamodb') as mock_db:
            mock_db.Table.return_value = mock_table
            history = TimeSeriesDynamoDBHistory(session_id='test_session')
        return history

    # ── add_message ───────────────────────────────────────────────────────────

    def test_add_message_calls_put_item(self):
        """add_message() phải gọi đúng 1 lần table.put_item()."""
        mock_table = MagicMock()
        history = self._make_history(mock_table)

        fake_msg = MagicMock(spec=_FakeBaseMessage)

        with patch.object(custom_memory, 'message_to_dict',
                          return_value={'type': 'human', 'data': {'content': 'Hello'}}):
            history.add_message(fake_msg)

        mock_table.put_item.assert_called_once()

    def test_add_message_item_has_required_keys(self):
        mock_table = MagicMock()
        history = self._make_history(mock_table)

        fake_msg = MagicMock(spec=_FakeBaseMessage)

        with patch.object(custom_memory, 'message_to_dict',
                          return_value={'type': 'human', 'data': {'content': 'Hi'}}):
            history.add_message(fake_msg)

        item = mock_table.put_item.call_args[1]['Item']
        assert item['chat_id'] == 'test_session'
        assert 'timestamp' in item
        assert 'message_data' in item

    def test_add_message_timestamp_is_decimal(self):
        mock_table = MagicMock()
        history = self._make_history(mock_table)

        fake_msg = MagicMock(spec=_FakeBaseMessage)
        with patch.object(custom_memory, 'message_to_dict', return_value={}):
            history.add_message(fake_msg)

        item = mock_table.put_item.call_args[1]['Item']
        assert isinstance(item['timestamp'], Decimal)

    def test_add_message_data_is_valid_json(self):
        mock_table = MagicMock()
        history = self._make_history(mock_table)

        fake_msg = MagicMock(spec=_FakeBaseMessage)
        payload = {'type': 'ai', 'data': {'content': 'Test response'}}
        with patch.object(custom_memory, 'message_to_dict', return_value=payload):
            history.add_message(fake_msg)

        item = mock_table.put_item.call_args[1]['Item']
        # Không được raise khi parse
        parsed = json.loads(item['message_data'])
        assert parsed == payload

    # ── messages property ─────────────────────────────────────────────────────

    def test_messages_returns_list_when_empty(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}   # không có LastEvaluatedKey
        history = self._make_history(mock_table)

        with patch.object(custom_memory, 'messages_from_dict', return_value=[]):
            result = history.messages

        assert isinstance(result, list)
        assert result == []

    def test_messages_pagination_queries_all_pages(self):
        mock_table = MagicMock()

        def _make_item(ts_val):
            return {
                'chat_id': 'test_session',
                'timestamp': Decimal(str(ts_val)),
                'message_data': json.dumps({'type': 'human', 'data': {'content': 'x'}})
            }

        mock_table.query.side_effect = [
            # Trang 1: có LastEvaluatedKey → phải query tiếp
            {
                'Items': [_make_item(1)],
                'LastEvaluatedKey': {'chat_id': 'test_session', 'timestamp': Decimal('1')}
            },
            # Trang 2: không có LastEvaluatedKey → dừng
            {
                'Items': [_make_item(2)]
            },
        ]

        history = self._make_history(mock_table)

        with patch.object(custom_memory, 'messages_from_dict', return_value=[MagicMock()]):
            history.messages

        assert mock_table.query.call_count == 2

    def test_messages_second_query_uses_exclusive_start_key(self):
        """Query trang 2 phải truyền ExclusiveStartKey từ LastEvaluatedKey của trang 1."""
        mock_table = MagicMock()
        last_key = {'chat_id': 'test_session', 'timestamp': Decimal('1')}

        mock_table.query.side_effect = [
            {'Items': [], 'LastEvaluatedKey': last_key},
            {'Items': []},
        ]
        history = self._make_history(mock_table)

        with patch.object(custom_memory, 'messages_from_dict', return_value=[]):
            history.messages

        second_call_kwargs = mock_table.query.call_args_list[1][1]
        assert second_call_kwargs.get('ExclusiveStartKey') == last_key

    def test_messages_sorted_ascending(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        history = self._make_history(mock_table)

        with patch.object(custom_memory, 'messages_from_dict', return_value=[]):
            history.messages

        first_call_kwargs = mock_table.query.call_args[1]
        assert first_call_kwargs.get('ScanIndexForward') is True

    # ── session_id ────────────────────────────────────────────────────────────

    def test_session_id_stored_as_string_from_int(self):
        mock_table = MagicMock()
        with patch.object(custom_memory, '_dynamodb') as mock_db:
            mock_db.Table.return_value = mock_table
            history = TimeSeriesDynamoDBHistory(session_id=12345)   # int
        assert history.session_id == '12345'
        assert isinstance(history.session_id, str)

    def test_session_id_stored_as_string_from_string(self):
        mock_table = MagicMock()
        with patch.object(custom_memory, '_dynamodb') as mock_db:
            mock_db.Table.return_value = mock_table
            history = TimeSeriesDynamoDBHistory(session_id='abc_123')
        assert history.session_id == 'abc_123'