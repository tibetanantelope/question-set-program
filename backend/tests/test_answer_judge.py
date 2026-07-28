from backend.services.learning_service.answer_judge import _parse_json_array


def test_parse_structured_ai_judgement():
    result = _parse_json_array(
        """```json
        [{"question_id":1,"verdict":"correct","confidence":0.95,
          "reason":"19元与19数值等价","error_type":null,"suggestion":""}]
        ```"""
    )
    assert result[0]["verdict"] == "correct"
    assert result[0]["confidence"] == 0.95
