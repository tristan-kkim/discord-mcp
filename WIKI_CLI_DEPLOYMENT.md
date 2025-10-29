# GitHub Wiki CLI 배포 가이드

## 🚀 자동화된 Wiki 배포

Discord MCP Server를 위한 Wiki를 CLI 환경에서 자동으로 배포할 수 있습니다.

### 📋 사전 요구사항

- GitHub CLI (`gh`) 설치됨
- GitHub 인증 완료 (`gh auth login`)
- Wiki 파일들이 `wiki/` 폴더에 준비됨

### 🔧 자동 배포 스크립트

프로젝트에 `wiki-deploy.sh` 스크립트가 포함되어 있습니다:

```bash
# 스크립트 실행
./wiki-deploy.sh
```

### 📝 수동 배포 방법

#### 1단계: GitHub에서 Wiki 활성화

1. **GitHub 저장소 접속**: https://github.com/tristan-kkim/discord-mcp
2. **Settings 탭 클릭**
3. **Features 섹션으로 스크롤**
4. **Wikis 체크박스 선택**
5. **Save 클릭**

#### 2단계: 첫 번째 페이지 생성

1. **Wiki 탭 클릭**: https://github.com/tristan-kkim/discord-mcp/wiki
2. **"Create the first page" 클릭**
3. **제목**: "Home"
4. **내용**: `wiki/Home.md` 파일 내용 복사
5. **"Create page" 클릭**

#### 3단계: 자동 배포 실행

```bash
# Wiki 배포 스크립트 실행
./wiki-deploy.sh
```

### 🎯 배포되는 Wiki 페이지들

1. **Home** - Wiki 홈페이지 및 네비게이션
2. **Installation Guide** - 상세한 설치 가이드
3. **Quick Start** - 5분 빠른 시작 가이드
4. **Channel Tools** - 채널 도구 완전 참조
5. **Security Guide** - 보안 가이드 및 모범 사례
6. **API Endpoints** - API 엔드포인트 완전 참조

### 🔗 Wiki 링크

Wiki가 배포되면 다음 URL에서 접근 가능:

- **Wiki 홈**: https://github.com/tristan-kkim/discord-mcp/wiki
- **설치 가이드**: https://github.com/tristan-kkim/discord-mcp/wiki/Installation-Guide
- **빠른 시작**: https://github.com/tristan-kkim/discord-mcp/wiki/Quick-Start
- **채널 도구**: https://github.com/tristan-kkim/discord-mcp/wiki/Channel-Tools
- **보안 가이드**: https://github.com/tristan-kkim/discord-mcp/wiki/Security-Guide
- **API 참조**: https://github.com/tristan-kkim/discord-mcp/wiki/API-Endpoints

### 🛠️ 스크립트 기능

`wiki-deploy.sh` 스크립트는 다음 기능을 제공합니다:

- ✅ GitHub CLI 인증 확인
- ✅ Wiki 활성화 상태 확인
- ✅ Wiki 저장소 자동 클론
- ✅ Wiki 파일 자동 복사
- ✅ Git 커밋 및 푸시
- ✅ 배포 상태 확인

### 📊 Wiki 특징

#### **전문적인 구조**
- 명확한 네비게이션 시스템
- 단계별 가이드 제공
- 완전한 API 참조 문서
- 보안 모범 사례 가이드

#### **실용적인 내용**
- 실제 사용 예시 (curl 명령어)
- 코드 샘플 (Python, JavaScript)
- 에러 처리 및 문제 해결
- 모니터링 및 배포 가이드

#### **포괄적인 문서화**
- 설치부터 프로덕션 배포까지
- 모든 30+ MCP 도구 설명
- 보안 고려사항 및 모범 사례
- 클라우드 배포 가이드

### 🚨 문제 해결

#### Wiki 저장소를 찾을 수 없음
```bash
# GitHub에서 Wiki를 활성화한 후 다시 시도
./wiki-deploy.sh
```

#### GitHub CLI 인증 오류
```bash
# GitHub CLI 재인증
gh auth login
```

#### 권한 오류
```bash
# 저장소 권한 확인
gh repo view tristan-kkim/discord-mcp
```

### 🎉 배포 완료 후

Wiki가 성공적으로 배포되면:

1. **README 업데이트**: Wiki 링크 추가
2. **커뮤니티 공유**: Discord, Twitter 등에서 공유
3. **피드백 수집**: 사용자 피드백 수집
4. **지속적 업데이트**: Wiki 내용 지속적 개선

### 📚 추가 리소스

- [GitHub Wiki 가이드](https://docs.github.com/en/communities/documenting-your-project-with-wikis)
- [GitHub CLI 문서](https://cli.github.com/manual/)
- [Markdown 가이드](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github)

---

## 🎯 요약

Discord MCP Server Wiki는 CLI 환경에서 자동으로 배포할 수 있습니다:

1. **GitHub에서 Wiki 활성화**
2. **첫 번째 페이지 생성**
3. **자동 배포 스크립트 실행**

모든 Wiki 파일이 준비되어 있으며, `./wiki-deploy.sh` 스크립트를 실행하면 자동으로 배포됩니다! 🚀
