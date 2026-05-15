# 마음나무 장애 대응 Troubleshooting

현장 장애 대응의 목표는 참가자 플로우, TV 표시, 관리자 지급을 빠르게 복구하는 것이다. 실제 참가자 원문, 개인정보, 운영 secret은 이 문서나 공유 로그에 남기지 않는다.

## 1. 참가자가 접속이 안 될 때

확인 순서:

1. QR URL이 현재 이벤트 slug와 맞는지 확인한다.
2. web container 상태를 확인한다.
3. API health를 확인한다.
4. 모바일 기기에서 같은 네트워크 또는 외부망 접근이 가능한지 확인한다.
5. CORS 설정의 `CORS_ORIGINS`가 실제 web origin과 맞는지 확인한다.

명령:

```bash
docker compose ps
curl http://localhost:8000/api/health
```

조치:

- web만 죽은 경우 web container를 재시작한다.
- API health가 실패하면 postgres 상태와 api 로그를 함께 확인한다.

## 2. 문항 제출 실패가 반복될 때

확인 순서:

1. API health 확인.
2. postgres container 상태 확인.
3. 참가자 화면의 재시도 UI가 표시되는지 확인.
4. 새로고침 후 세션 복구가 되는지 확인.
5. 같은 payload 재제출이 idempotent하게 처리되는지 backend test 결과를 확인.

참가자 안내:

- 브라우저를 바로 닫지 말고 재시도 버튼을 먼저 누르게 한다.
- 새로고침 후에도 진행 상태가 복구되는지 확인하게 한다.

## 3. LLM job이 실패할 때

확인 순서:

1. `.env`에서 `LLM_ENABLED`와 `LLM_PROVIDER` 확인.
2. `KEYWORD_FALLBACK_ENABLED=true` 확인.
3. 관리자 Keyword Jobs 화면에서 failed/retry_wait 상태 확인.
4. 필요 시 failed job을 관리자 화면에서 retry.
5. worker를 1회 실행한다.

명령:

```bash
docker compose exec api python -m app.scripts.run_keyword_worker --once
```

복구 기준:

- 외부 LLM이 실패해도 fallback keyword extraction으로 참가자 완료와 TV 운영이 이어져야 한다.
- 실제 API key를 문서나 채팅에 공유하지 않는다.

## 4. TV SSE가 끊겼을 때

확인 순서:

1. TV display route를 새로고침한다.
2. snapshot API가 응답하는지 확인한다.
3. API health를 확인한다.
4. TV가 마지막 snapshot을 유지하는지 확인한다.
5. API 복구 후 `connected` 상태와 최신 snapshot 수신을 확인한다.

명령:

```bash
curl http://localhost:8000/api/events/fire-expo-2026/display/snapshot
curl http://localhost:8000/api/health
```

수동 리허설:

1. `/display/fire-expo-2026` 접속.
2. initial snapshot 표시 확인.
3. SSE connected 상태 확인.
4. API 서버 재시작 또는 연결 차단.
5. 마지막 snapshot 유지 확인.
6. reconnecting 상태 확인.
7. API 복구 후 최신 snapshot 수신 확인.

## 5. 키워드가 TV에 안 보일 때

확인 순서:

1. keyword_jobs가 pending/failed/retry_wait인지 확인.
2. worker `--once` 실행.
3. keywords.status가 `active`인지 확인.
4. source card/reply가 `safety_status=safe`, `public_status=public`인지 확인.
5. source session의 `public_restriction` 또는 `crisis_expression_detected` 여부 확인.
6. 관리자가 keyword를 hidden/excluded 처리했는지 audit log 확인.

정책:

- hidden/excluded keyword는 TV에 표시되지 않는 것이 정상이다.
- public_restriction source의 keyword도 TV에 표시되지 않는 것이 정상이다.

## 6. 완료 코드가 조회되지 않을 때

확인 순서:

1. 참가자 세션이 complete page까지 도달했는지 확인.
2. completion_codes row가 있는지 확인.
3. 참가자 complete page를 새로고침해 코드 재조회.
4. 관리자 Rewards 화면에서 event slug와 code 입력값 확인.

주의:

- 이름, 전화번호, 소속으로 참가자를 검색하지 않는다.
- 완료 코드 기준으로만 지급한다.

## 7. 중복 지급 에러가 발생했을 때

확인 순서:

1. completion code status 확인.
2. `redeemedAt` 확인.
3. audit log에서 최초 지급 관리자와 시각 확인.
4. 참가자에게 이미 지급 처리된 코드임을 안내한다.

정책:

- `COMPLETION_CODE_ALREADY_REDEEMED`는 정상 보호 동작이다.
- 같은 코드를 다시 지급하지 않는다.

## 8. 개인정보 노출 의심

확인 순서:

1. 관리자 Cards/Replies 화면에서 해당 문장 hidden 또는 excluded 처리.
2. content redaction이 필요한 경우 원문을 덮어쓰지 말고 `content_redacted` 기준으로 공개.
3. 관련 keyword를 hidden/excluded 처리.
4. TV snapshot에서 제외되었는지 확인.
5. audit log에 조치가 남았는지 확인.

정책:

- TV API에는 원문, 점수, 위험 플래그, 세션 정보, 완료 코드가 나오면 안 된다.
- 장애 보고에 실제 참가자 원문이나 개인정보를 복사하지 않는다.
