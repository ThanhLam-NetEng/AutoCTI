import json
import time
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

_dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

class TimeSeriesDynamoDBHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, table_name: str = "autocti_conversations"):
        self.session_id = str(session_id)
        self.table = _dynamodb.Table(table_name)

    @property
    def messages(self):
        all_items = []
        kwargs = {
            'KeyConditionExpression': Key('chat_id').eq(self.session_id),
            'ScanIndexForward': True
        }
        while True:
            response = self.table.query(**kwargs)
            all_items.extend(response.get('Items', []))
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
            kwargs['ExclusiveStartKey'] = last_key

        result = []
        for item in all_items:
            msg_dict = json.loads(item['message_data'])
            result.extend(messages_from_dict([msg_dict]))
        return result

    def add_message(self, message: BaseMessage) -> None:
        ts = Decimal(str(time.time()))
        self.table.put_item(
            Item={
                'chat_id': self.session_id,
                'timestamp': ts,
                'message_data': json.dumps(message_to_dict(message), ensure_ascii=False)
            }
        )

    def clear(self) -> None:
        kwargs = {
            'KeyConditionExpression': Key('chat_id').eq(self.session_id),
            'ProjectionExpression': 'chat_id, #ts',
            'ExpressionAttributeNames': {'#ts': 'timestamp'}
        }
        while True:
            response = self.table.query(**kwargs)
            with self.table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(Key={
                        'chat_id': item['chat_id'],
                        'timestamp': item['timestamp']
                    })
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
            kwargs['ExclusiveStartKey'] = last_key
