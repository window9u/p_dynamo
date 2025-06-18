from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


# This is the data model for the session metadata in DynamoDB.
# it will be saved permanently in DynamoDB.
class SessionMetadata(BaseModel):
    user_id: str  # partition key
    session_id: str  # sort key, uuid v7(time based)
    created_at: int  # Number
    finished_at: Optional[int] = None  # Number
    session_summary: Optional[str] = None
    token_usage: Optional[int] = 0  # Number, total tokens used in the session


# This is the data model for the chatting in DynamoDB.
# it will be saved permanently in DynamoDB.
class Message(BaseModel):
    user_id: str  # partition key
    sort_key: str # sort key, session_id#created_at
    session_id: str  # 특정 세션의 메시지를 빠르게 찾기 위해 (GSI 사용할 수도 있음)
    created_at: int  # 메시지 발생 시각 (정렬 또는 쿼리/분석용)
    sender_type: str  # "human" or "ai"
    content: str  # 메시지 텍스트


class SenderType(Enum):
    HUMAN = "human"
    AI = "ai"


# This is the data model for the active session in DynamoDB.
# it will be saved temporally in DynamoDB.
class ActiveSession(BaseModel):
    user_id: str  # partition key
    session_id: str
    token_usage: int   # Number
    created_at: int  # Number
    updated_at: int  # Number
    expired_at: int


# This is the session for the active session in DynamoDB.
# it will be saved temporally in DynamoDB.
class LangChainSession(BaseModel):
    session_id: str  # partition key
    History: List


# Example of LangChainSession data structure
# {
#   "session_id": {
#     "S": "101945bf-4a5a-11f0-9800-8cb87eaa3cf4"
#   },
#   "History": {
#     "L": [
#       {
#         "M": {
#           "data": {
#             "M": {
#               "additional_kwargs": {
#                 "M": {}
#               },
#               "content": {
#                 "S": "나는 찬규"
#               },
#               "example": {
#                 "BOOL": false
#               },
#               "id": {
#                 "NULL": true
#               },
#               "name": {
#                 "NULL": true
#               },
#               "response_metadata": {
#                 "M": {}
#               },
#               "type": {
#                 "S": "human"
#               }
#             }
#           },
#           "type": {
#             "S": "human"
#           }
#         }
#       },
#       {
#         "M": {
#           "data": {
#             "M": {
#               "additional_kwargs": {
#                 "M": {
#                   "refusal": {
#                     "NULL": true
#                   }
#                 }
#               },
#               "content": {
#                 "S": "안녕하세요, 찬규님! 어떻게 도와드릴까요?"
#               },
#               "example": {
#                 "BOOL": false
#               },
#               "id": {
#                 "S": "run--e7a5a631-b352-4f25-8c0a-9cf9eff07052-0"
#               },
#               "invalid_tool_calls": {
#                 "L": []
#               },
#               "name": {
#                 "NULL": true
#               },
#               "response_metadata": {
#                 "M": {
#                   "finish_reason": {
#                     "S": "stop"
#                   },
#                   "id": {
#                     "S": "chatcmpl-Biu06yrKuvL48djklTyaIHwV7PJvr"
#                   },
#                   "logprobs": {
#                     "NULL": true
#                   },
#                   "model_name": {
#                     "S": "gpt-4o-mini-2024-07-18"
#                   },
#                   "service_tier": {
#                     "S": "default"
#                   },
#                   "system_fingerprint": {
#                     "S": "fp_34a54ae93c"
#                   },
#                   "token_usage": {
#                     "M": {
#                       "completion_tokens": {
#                         "N": "15"
#                       },
#                       "completion_tokens_details": {
#                         "M": {
#                           "accepted_prediction_tokens": {
#                             "N": "0"
#                           },
#                           "audio_tokens": {
#                             "N": "0"
#                           },
#                           "reasoning_tokens": {
#                             "N": "0"
#                           },
#                           "rejected_prediction_tokens": {
#                             "N": "0"
#                           }
#                         }
#                       },
#                       "prompt_tokens": {
#                         "N": "21"
#                       },
#                       "prompt_tokens_details": {
#                         "M": {
#                           "audio_tokens": {
#                             "N": "0"
#                           },
#                           "cached_tokens": {
#                             "N": "0"
#                           }
#                         }
#                       },
#                       "total_tokens": {
#                         "N": "36"
#                       }
#                     }
#                   }
#                 }
#               },
#               "tool_calls": {
#                 "L": []
#               },
#               "type": {
#                 "S": "ai"
#               },
#               "usage_metadata": {
#                 "M": {
#                   "input_tokens": {
#                     "N": "21"
#                   },
#                   "input_token_details": {
#                     "M": {
#                       "audio": {
#                         "N": "0"
#                       },
#                       "cache_read": {
#                         "N": "0"
#                       }
#                     }
#                   },
#                   "output_tokens": {
#                     "N": "15"
#                   },
#                   "output_token_details": {
#                     "M": {
#                       "audio": {
#                         "N": "0"
#                       },
#                       "reasoning": {
#                         "N": "0"
#                       }
#                     }
#                   },
#                   "total_tokens": {
#                     "N": "36"
#                   }
#                 }
#               }
#             }
#           },
#           "type": {
#             "S": "ai"
#           }
#         }
#       },
#       {
#         "M": {
#           "data": {
#             "M": {
#               "additional_kwargs": {
#                 "M": {}
#               },
#               "content": {
#                 "S": "내 이름은??"
#               },
#               "example": {
#                 "BOOL": false
#               },
#               "id": {
#                 "NULL": true
#               },
#               "name": {
#                 "NULL": true
#               },
#               "response_metadata": {
#                 "M": {}
#               },
#               "type": {
#                 "S": "human"
#               }
#             }
#           },
#           "type": {
#             "S": "human"
#           }
#         }
#       },
#       {
#         "M": {
#           "data": {
#             "M": {
#               "additional_kwargs": {
#                 "M": {
#                   "refusal": {
#                     "NULL": true
#                   }
#                 }
#               },
#               "content": {
#                 "S": "당신의 이름은 찬규입니다! 더 궁금한 것이나 도움이 필요하신 부분이 있으면 말씀해 주세요."
#               },
#               "example": {
#                 "BOOL": false
#               },
#               "id": {
#                 "S": "run--727bdf3f-c000-46b8-85e9-c4c5daf9f6d6-0"
#               },
#               "invalid_tool_calls": {
#                 "L": []
#               },
#               "name": {
#                 "NULL": true
#               },
#               "response_metadata": {
#                 "M": {
#                   "finish_reason": {
#                     "S": "stop"
#                   },
#                   "id": {
#                     "S": "chatcmpl-Biu0KZZziRv5IXSYyAhtBNzbmml0p"
#                   },
#                   "logprobs": {
#                     "NULL": true
#                   },
#                   "model_name": {
#                     "S": "gpt-4o-mini-2024-07-18"
#                   },
#                   "service_tier": {
#                     "S": "default"
#                   },
#                   "system_fingerprint": {
#                     "S": "fp_34a54ae93c"
#                   },
#                   "token_usage": {
#                     "M": {
#                       "completion_tokens": {
#                         "N": "28"
#                       },
#                       "completion_tokens_details": {
#                         "M": {
#                           "accepted_prediction_tokens": {
#                             "N": "0"
#                           },
#                           "audio_tokens": {
#                             "N": "0"
#                           },
#                           "reasoning_tokens": {
#                             "N": "0"
#                           },
#                           "rejected_prediction_tokens": {
#                             "N": "0"
#                           }
#                         }
#                       },
#                       "prompt_tokens": {
#                         "N": "48"
#                       },
#                       "prompt_tokens_details": {
#                         "M": {
#                           "audio_tokens": {
#                             "N": "0"
#                           },
#                           "cached_tokens": {
#                             "N": "0"
#                           }
#                         }
#                       },
#                       "total_tokens": {
#                         "N": "76"
#                       }
#                     }
#                   }
#                 }
#               },
#               "tool_calls": {
#                 "L": []
#               },
#               "type": {
#                 "S": "ai"
#               },
#               "usage_metadata": {
#                 "M": {
#                   "input_tokens": {
#                     "N": "48"
#                   },
#                   "input_token_details": {
#                     "M": {
#                       "audio": {
#                         "N": "0"
#                       },
#                       "cache_read": {
#                         "N": "0"
#                       }
#                     }
#                   },
#                   "output_tokens": {
#                     "N": "28"
#                   },
#                   "output_token_details": {
#                     "M": {
#                       "audio": {
#                         "N": "0"
#                       },
#                       "reasoning": {
#                         "N": "0"
#                       }
#                     }
#                   },
#                   "total_tokens": {
#                     "N": "76"
#                   }
#                 }
#               }
#             }
#           },
#           "type": {
#             "S": "ai"
#           }
#         }
#       }
#     ]
#   }
# }