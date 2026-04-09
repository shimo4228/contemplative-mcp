# ADR-0002: MCP 認知エンジンにはブリッジ層が必要

- **Status:** Accepted
- **Date:** 2026-04-10
- **Context:** akc-mcp を Claude Code 等の AI エージェントから利用する際の設計問題

## 問題

contemplative-agent の認知層を MCP ツールとして切り出した（akc-mcp）が、蒸留結果がクライアントエージェントの行動に反映されないことが判明した。

### 根本原因: 蒸留と行動の分離

- **contemplative-agent**: 蒸留も行動も同一プロセス。skills/, rules/, identity.md を自分で書いて自分で読む。サイクルが回る
- **akc-mcp**: 蒸留結果を MCP レスポンスとして返すだけ。クライアント側の skills/rules/identity には反映されない。サイクルが回らない

Claude Code が `distill` を呼んでも、結果は `~/.config/akc/` に閉じ、Claude Code 自身の `~/.claude/skills/` や `~/.claude/rules/` には何も起きない。

## 決定

akc-mcp をプラットフォーム非依存の **認知エンジン** と位置づけ、各エージェントプラットフォームへの反映は **ブリッジ層** が担う設計とする。

```
akc-mcp (認知エンジン — プラットフォーム非依存)
  ↓ 蒸留結果を返す
ブリッジ (プラットフォーム別アダプター)
  ↓ 適切な場所・形式に変換して書き込み
各エージェント:
  Claude Code → ~/.claude/skills/, ~/.claude/rules/
  Cursor      → .cursorrules
  Codex       → codex.md 等
  identity    → souls.md / CLAUDE.md にエイリアス
```

## 未解決の課題

- ブリッジ層の実装方法（MCP ツール内で行うか、外部スクリプトか、エージェント側フックか）
- プラットフォームごとのスキル・ルール形式の差異の吸収
- identity のマッピング（souls.md, CLAUDE.md 等へのエイリアスまたはシンボリックリンク）
- 承認ゲートとの整合性（蒸留結果を自動で書き込むか、人間の承認を挟むか）
- エピソードの入力元（各プラットフォームの活動ログをどう record_episode に流すか）

## 教訓

認知ツールを MCP として切り出すこと自体は正しいが、「結果を返す」だけでは不十分。蒸留サイクルを完結させるには、入力（エピソード記録）と出力（行動への反映）の両端をクライアントエージェントと接続する必要がある。
