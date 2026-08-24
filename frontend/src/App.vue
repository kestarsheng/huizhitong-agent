<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const view = ref('chat')
const agentType = ref('assistant')
const tenantId = ref(1)
const input = ref('')
const messages = ref([])
const agentCatalog = ref([])
const catalogLoading = ref(true)
const catalogError = ref('')
const streaming = ref(false)
const chatBody = ref(null)
let conversationId = 'conv-' + Date.now()
let typeTimer = null

const agents = [
  { value: 'assistant', label: '🤖 通用助手' },
  { value: 'knowledge', label: '📚 知识问答' },
  { value: 'inventory', label: '📦 库存分析' },
  { value: 'ticket', label: '🎫 工单处理' },
]

const chips = [
  { agent: 'knowledge', text: 'E-1024 故障代码怎么处理？' },
  { agent: 'inventory', text: '查一下商品 P1001 的库存与风险' },
  { agent: 'ticket', text: '打印机无法连接，请帮我创建报修工单' },
  { agent: 'assistant', text: '查一下 P1002 库存，顺便问 E-1024 怎么处理' },
  { agent: 'assistant', text: '你好，介绍一下你能做什么？' },
]

const NODE_LABELS = {
  classify_intent: { label: '意图分类', icon: '🧭' },
  plan_task: { label: '任务规划', icon: '🗺️' },
  inventory: { label: '库存查询', icon: '📦' },
  ticket: { label: '工单处理', icon: '🎫' },
  knowledge: { label: '知识检索', icon: '📚' },
  general: { label: '通用回答', icon: '💬' },
  validate_result: { label: '结果校验', icon: '✅' },
  synthesize_result: { label: '协同汇总', icon: '🤝' },
}

const STATUS_TEXT = {
  RUNNING: '编排运行中',
  PLANNED: '任务规划完成',
  CLASSIFIED: '意图已分类',
  COMPLETED: '回答完成',
  NEED_INPUT: '需要补充信息',
  FORBIDDEN: '工具未授权',
  WAITING_RAG: '知识检索完成',
  ERROR: '请求失败',
}

function nodeLabel(name) { const n = NODE_LABELS[name]; return n ? n.label : name }
function nodeIcon(name) { const n = NODE_LABELS[name]; return n ? n.icon : '⚙️' }
function statusText(s) { return STATUS_TEXT[s] || s || '' }

function scrollBottom() {
  requestAnimationFrame(() => {
    const el = chatBody.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function newChat() {
  messages.value = []
  conversationId = 'conv-' + Date.now()
  input.value = ''
  streaming.value = false
}

function finishAnswer(msg) {
  if (!msg.text) msg.text = '（未返回内容）'
  const full = msg.text
  msg.text = ''
  let i = 0
  clearInterval(typeTimer)
  typeTimer = setInterval(() => {
    i = Math.min(full.length, i + 3)
    msg.text = full.slice(0, i)
    scrollBottom()
    if (i >= full.length) {
      clearInterval(typeTimer)
      msg.done = true
    }
  }, 10)
}

function handleEvent(msg, raw) {
  const lines = raw.split('\n')
  let event = 'message'
  const dataLines = []
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  const data = dataLines.join('')
  if (!data) return
  let payload
  try { payload = JSON.parse(data) } catch { return }
  if (event === 'accepted') {
    msg.status = 'RUNNING'
  } else if (event === 'node') {
    const pill = { node: payload.node, state: payload.state || {} }
    const last = msg.nodes[msg.nodes.length - 1]
    if (last && last.node === pill.node) last.state = pill.state
    else msg.nodes.push(pill)
    const st = payload.state && payload.state.status
    if (st && st !== 'RUNNING') msg.status = st
    scrollBottom()
  } else if (event === 'done') {
    msg.status = payload.status || 'COMPLETED'
    msg.text = payload.answer || ''
    finishAnswer(msg)
  }
}

function answerHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || streaming.value) return
  messages.value.push({ role: 'user', text })
  const msg = { role: 'assistant', text: '', nodes: [], status: 'RUNNING', done: false, error: '' }
  messages.value.push(msg)
  input.value = ''
  streaming.value = true
  scrollBottom()
  try {
    const res = await fetch('/api/agent/agents/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_type: agentType.value,
        conversation_id: conversationId,
        message: text,
        tenant_id: tenantId.value,
        stream: true,
      }),
    })
    if (!res.ok || !res.body) throw new Error('Agent Runtime 未就绪（HTTP ' + res.status + '），请确认 8000 端口已启动')
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      let sep
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        handleEvent(msg, buffer.slice(0, sep))
        buffer = buffer.slice(sep + 2)
      }
    }
    if (buffer.trim()) handleEvent(msg, buffer)
    if (!msg.done) finishAnswer(msg)
  } catch (e) {
    msg.error = e.message || '请求失败'
    msg.status = 'ERROR'
    msg.done = true
  } finally {
    streaming.value = false
    scrollBottom()
  }
}

function useChip(chip) {
  agentType.value = chip.agent
  input.value = chip.text
  sendMessage()
}

/* ---------- 工具目录 ---------- */
const tools = ref([])
const loading = ref(true)
const error = ref('')
const showForm = ref(false)
const form = ref({ toolName: '', serverName: '', description: '' })
const active = computed(() => tools.value.filter(t => t.enabled === 1).length)

async function loadTools() {
  loading.value = true
  try {
    const health = await fetch('/api/internal/health')
    if (!health.ok) throw new Error('工具服务健康检查失败')
    const response = await fetch('/api/internal/tools')
    if (!response.ok) throw new Error('工具服务暂不可用')
    tools.value = await response.json()
    error.value = ''
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

async function loadAgentCatalog() {
  catalogLoading.value = true
  try {
    const response = await fetch('/api/agent/agents/catalog')
    if (!response.ok) throw new Error('Agent Runtime 暂不可用')
    agentCatalog.value = await response.json()
    catalogError.value = ''
  } catch (e) { catalogError.value = e.message }
  finally { catalogLoading.value = false }
}

async function toggleTool(tool) {
  const next = tool.enabled !== 1
  const response = await fetch('/api/internal/tools/' + tool.id + '/status?enabled=' + next, { method: 'PATCH' })
  if (!response.ok) { error.value = '工具状态更新失败'; return }
  await loadTools()
}

async function registerTool() {
  const response = await fetch('/api/internal/tools', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form.value, inputSchema: '{}', enabled: 1 }),
  })
  if (!response.ok) { error.value = '工具注册失败'; return }
  form.value = { toolName: '', serverName: '', description: '' }
  showForm.value = false
  await loadTools()
}

/* ---------- 知识库 ---------- */
const docs = ref([])
const kbLoading = ref(true)
const kbError = ref('')
const kbShowForm = ref(false)
const kbForm = ref({ documentId: '', content: '', tenantId: 'default' })
const totalChunks = computed(() => docs.value.reduce((sum, doc) => sum + doc.chunk_count, 0))

async function loadKnowledge() {
  kbLoading.value = true
  try {
    const response = await fetch('/api/agent/knowledge/documents')
    if (!response.ok) throw new Error('Agent Runtime 暂不可用')
    docs.value = await response.json()
    kbError.value = ''
  } catch (e) { kbError.value = e.message }
  finally { kbLoading.value = false }
}

async function addDocument() {
  const response = await fetch('/api/agent/knowledge/documents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: kbForm.value.documentId, content: kbForm.value.content, tenant_id: kbForm.value.tenantId }),
  })
  if (!response.ok) { kbError.value = response.status === 409 ? '文档 ID 已存在' : '文档入库失败'; return }
  kbForm.value = { documentId: '', content: '', tenantId: 'default' }
  kbShowForm.value = false
  await loadKnowledge()
}

const audits = ref([])
const auditLoading = ref(false)
const auditError = ref('')
const auditFilter = ref('')
const auditTotal = computed(() => audits.value.length)
const auditAvg = computed(() => audits.value.length ? Math.round(audits.value.reduce((sum, item) => sum + (item.latency_ms || 0), 0) / audits.value.length) : 0)
const auditDone = computed(() => audits.value.filter(item => item.status === 'COMPLETED').length)

function statusClass(status) {
  if (status === 'COMPLETED') return 'ok'
  if (status === 'WAITING_RAG' || status === 'NEED_INPUT') return 'warn'
  if (status === 'FORBIDDEN' || status === 'ERROR') return 'bad'
  return 'info'
}

function formatTime(value) {
  if (!value) return '-'
  const date = new Date(String(value).replace(' ', 'T'))
  if (isNaN(date.getTime())) return String(value)
  const pad = n => String(n).padStart(2, '0')
  return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) + ' ' + pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds())
}

async function loadAudits() {
  auditLoading.value = true
  try {
    const query = auditFilter.value ? '?agent_type=' + encodeURIComponent(auditFilter.value) : ''
    const response = await fetch('/api/agent/audit/calls' + query)
    if (!response.ok) throw new Error('审计服务暂不可用')
    audits.value = await response.json()
    auditError.value = ''
  } catch (e) { auditError.value = e.message }
  finally { auditLoading.value = false }
}

onMounted(() => { loadTools(); loadAgentCatalog(); loadKnowledge(); loadAudits() })
onBeforeUnmount(() => clearInterval(typeTimer))
</script>

<template>
  <main class="shell">
    <aside class="rail">
      <div class="brand">
        <div class="mark">HZ</div>
        <div class="brand-text">汇智通<span>AI CONTROL</span></div>
      </div>
      <nav>
        <a :class="{ selected: view === 'chat' }" @click="view = 'chat'">智能体对话</a>
        <a :class="{ selected: view === 'agents' }" @click="view = 'agents'">智能体目录</a>
        <a :class="{ selected: view === 'tools' }" @click="view = 'tools'">工具目录</a>
        <a :class="{ selected: view === 'knowledge' }" @click="view = 'knowledge'">知识库</a>
        <a :class="{ selected: view === 'audit' }" @click="view = 'audit'">调用审计</a>
      </nav>
      <div class="rail-foot"><i class="pulse"></i>LOCAL / DEV · v0.2</div>
    </aside>

    <section class="content">
      <!-- ============ 智能体对话 ============ -->
      <template v-if="view === 'chat'">
        <header>
          <div>
            <p class="eyebrow">AGENT CONSOLE / LIVE CONVERSATION</p>
            <h1>智能体对话</h1>
            <p class="sub">选择智能体类型，体验 LangGraph 多智能体编排、RAG 知识问答与 MCP 工具调用。</p>
          </div>
          <div class="actions">
            <select v-model="agentType" class="agent-select">
              <option v-for="a in agents" :key="a.value" :value="a.value">{{ a.label }}</option>
            </select>
            <input v-model.number="tenantId" class="tenant-input" type="number" min="1" placeholder="租户 ID" />
            <button @click="newChat">新会话</button>
          </div>
        </header>

        <div ref="chatBody" class="chat-body">
          <div v-if="messages.length === 0" class="chat-empty">
            <div class="orb">🤖</div>
            <h2>开始对话</h2>
            <p>试试下面的示例问题，或直接输入你的问题。</p>
            <div class="chips">
              <button v-for="chip in chips" :key="chip.text" class="chip" @click="useChip(chip)">{{ chip.text }}</button>
            </div>
          </div>

          <div v-for="(msg, i) in messages" :key="i" :class="['row', msg.role]">
            <div v-if="msg.role === 'assistant'" class="avatar">🤖</div>
            <div class="bubble-wrap">
              <div :class="['bubble', msg.role]">
                <template v-if="msg.role === 'assistant'">
                  <div v-if="msg.nodes.length" class="nodes">
                    <span v-for="(node, ni) in msg.nodes" :key="ni" :class="['node-pill', { active: streaming && ni === msg.nodes.length - 1 && !msg.done, done: msg.done }]">
                      {{ nodeIcon(node.node) }} {{ nodeLabel(node.node) }}
                    </span>
                    <span v-if="streaming && !msg.nodes.length" class="node-pill active">⏳ 正在启动编排…</span>
                  </div>
                  <div v-if="!msg.text && !msg.done" class="thinking">……</div>
                  <p v-else class="answer" v-html="answerHtml(msg.text)"></p>
                  <p v-if="msg.error" class="error-text">{{ msg.error }}</p>
                </template>
                <template v-else>{{ msg.text }}</template>
              </div>
              <div v-if="msg.role === 'assistant' && msg.status" class="meta">
                {{ statusText(msg.status) }}{{ msg.nodes.length ? ' · ' + msg.nodes.length + ' 个节点' : '' }}
              </div>
            </div>
          </div>
        </div>

        <footer class="composer">
          <div v-if="messages.length" class="chips inline-chips">
            <button v-for="chip in chips" :key="chip.text" class="chip small" @click="useChip(chip)">{{ chip.text }}</button>
          </div>
          <div class="input-bar">
            <textarea v-model="input" rows="1" :disabled="streaming" placeholder="输入问题，Enter 发送，Shift+Enter 换行…" @keydown.enter.exact.prevent="sendMessage"></textarea>
            <button class="send" :disabled="streaming || !input.trim()" @click="sendMessage">{{ streaming ? '运行中…' : '发送' }}</button>
          </div>
        </footer>
      </template>

      <!-- ============ 智能体目录 ============ -->
      <template v-else-if="view === 'agents'">
        <header>
          <div>
            <p class="eyebrow">AGENT MESH / A2A DIRECTORY</p>
            <h1>智能体目录</h1>
            <p class="sub">A2A 跨智能体协同：客服智能体识别意图后，并行转发给专业智能体并协同汇总答复。</p>
          </div>
          <div class="actions">
            <button @click="loadAgentCatalog">刷新目录 ↻</button>
          </div>
        </header>
        <div class="stats">
          <div><span>注册智能体</span><strong>{{ agentCatalog.length }}</strong></div>
          <div><span>协同入口</span><strong class="online">客服智能体</strong></div>
          <div><span>路由模式</span><strong>LLM / 规则</strong></div>
        </div>
        <div v-if="catalogLoading" class="empty">正在读取智能体注册中心…</div>
        <div v-else-if="catalogError" class="empty danger">{{ catalogError }}<button @click="loadAgentCatalog">重试</button></div>
        <div v-else class="tool-grid">
          <article v-for="agent in agentCatalog" :key="agent.agent_id" class="tool-card">
            <div class="card-top">
              <span class="tool-id">AGENT / {{ agent.agent_id.toUpperCase() }}</span>
              <i class="dot on"></i>
            </div>
            <h2>{{ agent.name }}</h2>
            <p>{{ agent.description }}</p>
            <div class="server">节点 {{ agent.node }}<span v-if="agent.tools.length"> · 工具 {{ agent.tools.join('、') }}</span></div>
          </article>
        </div>
      </template>

      <!-- ============ 工具目录 ============ -->
      <template v-else-if="view === 'tools'">
        <header>
          <div>
            <p class="eyebrow">CONTROL ROOM / TOOL REGISTRY</p>
            <h1>工具目录</h1>
            <p class="sub">统一查看 MCP Server 暴露给智能体的业务能力。</p>
          </div>
          <div class="actions">
            <button @click="showForm = !showForm">{{ showForm ? '取消注册' : '+ 注册工具' }}</button>
            <button @click="loadTools">刷新目录 ↻</button>
          </div>
        </header>
        <form v-if="showForm" class="register-form" @submit.prevent="registerTool">
          <input v-model="form.toolName" required placeholder="工具名称，如 create_ticket">
          <input v-model="form.serverName" required placeholder="MCP Server，如 ticket-server">
          <input v-model="form.description" placeholder="工具描述">
          <button type="submit">保存工具</button>
        </form>
        <div class="stats">
          <div><span>已注册工具</span><strong>{{ tools.length }}</strong></div>
          <div><span>当前启用</span><strong>{{ active }}</strong></div>
          <div><span>连接状态</span><strong class="online">{{ error ? 'OFFLINE' : 'ONLINE' }}</strong></div>
        </div>
        <div v-if="loading" class="empty">正在读取工具注册中心…</div>
        <div v-else-if="error" class="empty danger">{{ error }}<button @click="loadTools">重试</button></div>
        <div v-else class="tool-grid">
          <article v-for="tool in tools" :key="tool.id" class="tool-card">
            <div class="card-top">
              <span class="tool-id">TOOL / {{ String(tool.id).padStart(2, '0') }}</span>
              <i :class="['dot', tool.enabled === 1 ? 'on' : 'off']"></i>
            </div>
            <h2>{{ tool.toolName }}</h2>
            <p>{{ tool.description }}</p>
            <div class="server">↳ {{ tool.serverName }} <span>{{ tool.enabled === 1 ? '已启用' : '已停用' }}</span></div>
            <button class="toggle" @click="toggleTool(tool)">{{ tool.enabled === 1 ? '停用工具' : '启用工具' }}</button>
          </article>
        </div>
      </template>

      <!-- ============ 调用审计 ============ -->
      <template v-else-if="view === 'audit'">
        <header>
          <div>
            <p class="eyebrow">CONTROL ROOM / CALL AUDIT</p>
            <h1>调用审计</h1>
            <p class="sub">智能体调用记录异步落库：优先 RabbitMQ 发布，由独立 worker 写 MySQL；MQ 不可用时自动降级直写。</p>
          </div>
          <div class="actions">
            <select v-model="auditFilter" class="agent-select" @change="loadAudits">
              <option value="">全部智能体</option>
              <option value="assistant">通用助手</option>
              <option value="knowledge">知识问答</option>
              <option value="inventory">库存分析</option>
              <option value="ticket">工单处理</option>
            </select>
            <button @click="loadAudits">刷新 ↻</button>
          </div>
        </header>
        <div class="stats">
          <div><span>已记录调用</span><strong>{{ auditTotal }}</strong></div>
          <div><span>平均耗时</span><strong>{{ auditAvg }} ms</strong></div>
          <div><span>已完成</span><strong class="online">{{ auditDone }}</strong></div>
        </div>
        <div v-if="auditLoading" class="empty">正在读取调用记录…</div>
        <div v-else-if="auditError" class="empty danger">{{ auditError }}<button @click="loadAudits">重试</button></div>
        <div v-else class="audit-wrap">
          <table class="audit-table">
            <thead>
              <tr><th>时间</th><th>会话</th><th>智能体</th><th>问题</th><th>状态</th><th>节点</th><th>耗时</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in audits" :key="item.id">
                <td class="mono">{{ formatTime(item.created_at) }}</td>
                <td class="mono">{{ item.conversation_id }}</td>
                <td>{{ item.agent_type }}</td>
                <td class="msg" :title="item.message">{{ item.message }}</td>
                <td><span :class="['badge', statusClass(item.status)]">{{ item.status }}</span></td>
                <td class="mono">{{ item.node_count }}</td>
                <td class="mono">{{ item.latency_ms }} ms</td>
              </tr>
              <tr v-if="audits.length === 0"><td colspan="7" class="empty-row">暂无调用记录</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- ============ 知识库 ============ -->
      <template v-else>
        <header>
          <div>
            <p class="eyebrow">CONTROL ROOM / KNOWLEDGE BASE</p>
            <h1>知识库</h1>
            <p class="sub">管理 RAG 知识文档，切片入库后供智能体检索回答。</p>
          </div>
          <div class="actions">
            <button @click="kbShowForm = !kbShowForm">{{ kbShowForm ? '取消添加' : '+ 添加文档' }}</button>
            <button @click="loadKnowledge">刷新目录 ↻</button>
          </div>
        </header>
        <form v-if="kbShowForm" class="register-form" @submit.prevent="addDocument">
          <input v-model="kbForm.documentId" required placeholder="文档 ID，如 return-policy">
          <input v-model="kbForm.tenantId" required placeholder="租户 ID，如 default">
          <textarea v-model="kbForm.content" required placeholder="文档内容，保存后自动切片入库" rows="3"></textarea>
          <button type="submit">保存文档</button>
        </form>
        <div class="stats">
          <div><span>知识文档</span><strong>{{ docs.length }}</strong></div>
          <div><span>切片总数</span><strong>{{ totalChunks }}</strong></div>
          <div><span>连接状态</span><strong class="online">{{ kbError ? 'OFFLINE' : 'ONLINE' }}</strong></div>
        </div>
        <div v-if="kbLoading" class="empty">正在读取知识库…</div>
        <div v-else-if="kbError" class="empty danger">{{ kbError }}<button @click="loadKnowledge">重试</button></div>
        <div v-else class="tool-grid">
          <article v-for="doc in docs" :key="doc.document_id" class="tool-card">
            <div class="card-top">
              <span class="tool-id">DOC / {{ doc.document_id }}</span>
              <i class="dot on"></i>
            </div>
            <h2>{{ doc.document_id }}</h2>
            <p>所属租户：{{ doc.tenant_id }}</p>
            <div class="server">↳ {{ doc.chunk_count }} 个切片 <span>已入库</span></div>
          </article>
        </div>
      </template>
    </section>
  </main>
</template>

<style>
:root {
  font-family: 'Manrope', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #17345a;
  --panel: #ffffff;
  --line: #d8e6f6;
  --ink: #17345a;
  --ink-2: #3f6289;
  --muted: #7c93b1;
  --blue: #2f7fe0;
  --blue-deep: #1d63bd;
  --blue-soft: #e6f1fd;
  --cyan: #18a9d2;
  --good: #12a878;
  --danger: #e05c6b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at 80% -10%, #d5e9ff 0%, #eef5fd 45%);
  min-height: 100vh;
}
.shell { display: flex; min-height: 100vh; max-width: 1440px; margin: 0 auto; }
.rail {
  width: 224px;
  flex: none;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 26px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(18px);
  border-right: 1px solid var(--line);
  position: sticky;
  top: 0;
  height: 100vh;
}
.brand { display: flex; align-items: center; gap: 12px; }
.mark {
  width: 44px; height: 44px; border-radius: 14px;
  background: linear-gradient(135deg, #76dfff, #2f7fe0);
  display: grid; place-items: center;
  color: #fff; font-weight: 800; letter-spacing: 0.5px;
  box-shadow: 0 10px 26px rgba(47, 127, 224, 0.35);
}
.brand-text { font-weight: 800; font-size: 17px; line-height: 1.2; }
.brand-text span { display: block; font-size: 10px; font-weight: 700; letter-spacing: 0.22em; color: var(--muted); }
nav { display: flex; flex-direction: column; gap: 6px; }
nav a {
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 14px; border-radius: 12px;
  color: #5d7a9c; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: 0.18s ease; text-decoration: none;
}
nav a:hover { background: var(--blue-soft); color: var(--blue-deep); }
nav a.selected { color: var(--blue-deep); background: var(--blue-soft); box-shadow: inset 3px 0 var(--blue); }
nav a.soon { opacity: 0.55; cursor: default; }
nav a.soon em {
  font-size: 10px; font-style: normal; color: var(--muted);
  background: #eaf1fa; border-radius: 99px; padding: 2px 8px;
}
.rail-foot {
  display: flex; align-items: center; gap: 8px; margin-top: auto;
  font-size: 11px; letter-spacing: 0.12em; color: var(--muted);
}
.pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--good); box-shadow: 0 0 0 0 rgba(18, 168, 120, 0.45);
  animation: pulse 2s infinite;
}
@keyframes pulse { 70% { box-shadow: 0 0 0 8px rgba(18, 168, 120, 0); } 100% { box-shadow: 0 0 0 0 rgba(18, 168, 120, 0); } }
.content { flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 38px 42px 26px; }
.eyebrow { font-size: 11px; letter-spacing: 0.22em; font-weight: 800; color: var(--blue); margin: 0 0 8px; }
h1 { font-size: 26px; margin: 0 0 6px; color: var(--ink); }
.sub { font-size: 13px; color: var(--muted); margin: 0; }
header { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; margin-bottom: 22px; }
.actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
button {
  font: inherit; border: 1px solid var(--blue); background: var(--blue); color: #fff;
  border-radius: 11px; padding: 9px 16px; font-size: 13px; font-weight: 700;
  cursor: pointer; transition: 0.18s ease;
  box-shadow: 0 6px 16px rgba(47, 127, 224, 0.24);
}
button:hover:not(:disabled) { background: var(--blue-deep); border-color: var(--blue-deep); transform: translateY(-1px); }
button:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }
.agent-select, .tenant-input {
  border: 1px solid var(--line); background: #fff; border-radius: 11px;
  padding: 9px 12px; color: var(--ink); font: 13px Manrope, sans-serif;
  outline: none; transition: 0.18s ease;
}
.agent-select:focus, .tenant-input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(47, 127, 224, 0.15); }
.tenant-input { width: 96px; }

/* ---------- 对话区 ---------- */
.chat-body {
  flex: 1; min-height: 420px; max-height: calc(100vh - 340px);
  overflow-y: auto; padding: 6px 4px 18px;
  display: flex; flex-direction: column; gap: 18px;
  scroll-behavior: smooth;
}
.chat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin: auto; gap: 6px; }
.orb {
  width: 72px; height: 72px; border-radius: 22px;
  background: linear-gradient(135deg, #e8f3ff, #d9ecff);
  display: grid; place-items: center; font-size: 32px;
  box-shadow: 0 14px 34px rgba(47, 127, 224, 0.18);
  margin-bottom: 8px;
}
.chat-empty h2 { margin: 0; font-size: 18px; color: var(--ink); }
.chat-empty p { margin: 0 0 12px; font-size: 13px; color: var(--muted); }
.chips { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.chip {
  background: #fff; border: 1px solid var(--line); color: var(--blue-deep);
  border-radius: 99px; padding: 8px 14px; font-size: 12px; font-weight: 600;
  box-shadow: none;
}
.chip:hover { background: var(--blue-soft); border-color: #a9cdf5; color: var(--blue-deep); transform: none; }
.chip.small { padding: 5px 12px; font-size: 11px; }
.inline-chips { justify-content: flex-start; margin-bottom: 10px; }
.row { display: flex; gap: 10px; align-items: flex-start; }
.row.user { justify-content: flex-end; }
.avatar {
  width: 34px; height: 34px; flex: none; border-radius: 12px;
  background: linear-gradient(135deg, #76dfff, #2f7fe0);
  display: grid; place-items: center; font-size: 16px;
  box-shadow: 0 6px 14px rgba(47, 127, 224, 0.25);
}
.bubble-wrap { max-width: 78%; display: flex; flex-direction: column; }
.bubble { padding: 13px 16px; border-radius: 18px; font-size: 14px; line-height: 1.65; word-break: break-word; }
.bubble.assistant { background: #fff; border: 1px solid var(--line); border-top-left-radius: 6px; box-shadow: 0 8px 20px rgba(55, 94, 140, 0.08); }
.bubble.user {
  background: linear-gradient(135deg, #3b8bf0, #2f7fe0); color: #fff;
  border-top-right-radius: 6px; box-shadow: 0 8px 20px rgba(47, 127, 224, 0.28);
  white-space: pre-wrap; align-self: flex-end;
}
.nodes { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.node-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11.5px; font-weight: 700; color: var(--blue-deep);
  background: var(--blue-soft); border: 1px solid #c6dffb;
  border-radius: 99px; padding: 4px 11px;
}
.node-pill.active { animation: softpulse 1.2s infinite; }
.node-pill.done::after { content: ' ✓'; color: var(--good); }
@keyframes softpulse { 50% { background: #d7e9ff; } }
.thinking { color: var(--muted); font-size: 15px; letter-spacing: 2px; animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0.35; } }
.answer { margin: 0; }
.error-text { margin: 8px 0 0; color: var(--danger); font-weight: 600; font-size: 13px; }
.meta { margin-top: 5px; font-size: 11px; color: var(--muted); }

/* ---------- 输入区 ---------- */
.composer { position: sticky; bottom: 0; padding-top: 14px; background: linear-gradient(180deg, rgba(238, 245, 253, 0), #eef5fd 30%); }
.input-bar {
  display: flex; gap: 10px; align-items: flex-end;
  background: #fff; border: 1px solid var(--line); border-radius: 16px;
  padding: 10px 10px 10px 14px;
  box-shadow: 0 12px 30px rgba(47, 127, 224, 0.12);
}
.input-bar textarea {
  flex: 1; border: none; outline: none; resize: none;
  font: 14px/1.55 Manrope, sans-serif; color: var(--ink);
  background: transparent; max-height: 140px; padding: 7px 0;
}
.send { flex: none; border-radius: 12px; padding: 10px 20px; }

/* ---------- 工具 / 知识库 ---------- */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 22px; }
.stats div {
  background: rgba(255, 255, 255, 0.9); border: 1px solid var(--line);
  border-radius: 15px; padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(55, 94, 140, 0.08);
}
.stats span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.stats strong { font-size: 22px; color: var(--ink); }
.online { color: var(--good); }
.tool-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.tool-card {
  background: rgba(255, 255, 255, 0.92); border: 1px solid var(--line);
  border-radius: 17px; padding: 18px; display: flex; flex-direction: column;
  box-shadow: 0 12px 28px rgba(55, 94, 140, 0.09); transition: 0.22s ease;
}
.tool-card:hover { transform: translateY(-4px); border-color: #9ec6f2; box-shadow: 0 18px 40px rgba(47, 127, 224, 0.16); }
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.tool-id { font-size: 10px; letter-spacing: 0.16em; font-weight: 800; color: #86a2c4; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #c3d2e6; }
.dot.on { background: var(--good); box-shadow: 0 0 12px rgba(18, 168, 120, 0.4); }
.tool-card h2 { margin: 0 0 6px; font-size: 16px; color: var(--ink); }
.tool-card p { margin: 0 0 12px; font-size: 13px; color: var(--muted); line-height: 1.55; flex: 1; }
.server { font-size: 12px; color: #178fb8; display: flex; justify-content: space-between; align-items: center; }
.server span { color: var(--muted); }
.tool-card .toggle { margin-top: 16px; align-self: flex-start; padding: 7px 14px; font-size: 12px; }
.register-form {
  display: grid; grid-template-columns: 1fr 1fr 1.4fr auto; gap: 10px;
  margin: 0 0 18px; padding: 16px; background: #fff;
  border: 1px solid var(--line); border-radius: 16px;
  box-shadow: 0 10px 24px rgba(55, 94, 140, 0.08);
}
.register-form input, .register-form textarea {
  border: 1px solid var(--line); border-radius: 10px; padding: 11px 12px;
  color: var(--ink); font: 13px Manrope, sans-serif; outline: none; background: #fff;
}
.register-form input:focus, .register-form textarea:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(47, 127, 224, 0.14); }
.register-form textarea { grid-column: 1 / -1; resize: vertical; }
.empty { text-align: center; padding: 44px 0; color: var(--muted); font-size: 13px; }
.empty.danger { color: var(--danger); }
.empty button { margin-top: 14px; }

.audit-wrap { background: #fff; border: 1px solid var(--line); border-radius: 16px; box-shadow: 0 12px 28px rgba(55, 94, 140, 0.09); overflow: auto; }
.audit-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.audit-table th { text-align: left; padding: 13px 16px; font-size: 11px; letter-spacing: 0.12em; color: var(--muted); background: var(--blue-soft); border-bottom: 1px solid var(--line); white-space: nowrap; }
.audit-table td { padding: 12px 16px; border-bottom: 1px solid #eaf1f9; color: var(--ink-2); vertical-align: middle; }
.audit-table tr:last-child td { border-bottom: none; }
.audit-table tr:hover td { background: #f7fbff; }
.audit-table .msg { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mono { font-family: 'DM Mono', monospace; font-size: 12px; color: var(--muted); white-space: nowrap; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 700; }
.badge.ok { color: var(--good); background: #e4f7f0; }
.badge.warn { color: #b7791f; background: #fdf3e1; }
.badge.bad { color: var(--danger); background: #fde9ec; }
.badge.info { color: var(--blue-deep); background: var(--blue-soft); }
.empty-row { text-align: center; color: var(--muted); padding: 30px 0; }

@media (max-width: 860px) {
  .rail { width: 76px; padding: 20px 10px; }
  .brand-text, .rail nav a span, .rail nav a em, .rail-foot { display: none; }
  nav a { justify-content: center; padding: 11px; }
  .content { padding: 26px 18px 20px; }
  .bubble-wrap { max-width: 92%; }
  .register-form { grid-template-columns: 1fr; }
  .register-form textarea { grid-column: auto; }
  .chat-body { max-height: calc(100vh - 300px); }
}
</style>
