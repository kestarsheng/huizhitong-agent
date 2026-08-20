<script setup>
import { computed, onMounted, ref } from 'vue'

const view = ref('tools')
const tools = ref([])
const loading = ref(true)
const error = ref('')
const showForm = ref(false)
const form = ref({ toolName: '', serverName: '', description: '' })
const active = computed(() => tools.value.filter(item => item.enabled === 1).length)

const docs = ref([])
const kbLoading = ref(true)
const kbError = ref('')
const kbShowForm = ref(false)
const kbForm = ref({ documentId: '', content: '', tenantId: 'default' })
const totalChunks = computed(() => docs.value.reduce((sum, doc) => sum + doc.chunk_count, 0))

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

async function toggleTool(tool) {
  const next = tool.enabled !== 1
  const response = await fetch(`/api/internal/tools/${tool.id}/status?enabled=${next}`, { method: 'PATCH' })
  if (!response.ok) { error.value = '工具状态更新失败'; return }
  await loadTools()
}

async function registerTool() {
  const response = await fetch('/api/internal/tools', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form.value, inputSchema: '{}', enabled: 1 }) })
  if (!response.ok) { error.value = '工具注册失败'; return }
  form.value = { toolName: '', serverName: '', description: '' }; showForm.value = false; await loadTools()
}

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
    body: JSON.stringify({ document_id: kbForm.value.documentId, content: kbForm.value.content, tenant_id: kbForm.value.tenantId })
  })
  if (!response.ok) { kbError.value = response.status === 409 ? '文档 ID 已存在' : '文档入库失败'; return }
  kbForm.value = { documentId: '', content: '', tenantId: 'default' }
  kbShowForm.value = false
  await loadKnowledge()
}

onMounted(() => { loadTools(); loadKnowledge() })
</script>

<template>
  <main class="shell">
    <aside class="rail"><div class="mark">HZ</div><div class="rail-label">汇智通<br><span>AI CONTROL</span></div><nav><a :class="{ selected: view === 'tools' }" @click="view = 'tools'">工具目录</a><a>智能体</a><a :class="{ selected: view === 'knowledge' }" @click="view = 'knowledge'">知识库</a><a>调用审计</a></nav><div class="rail-foot">LOCAL / DEV</div></aside>
    <section class="content">
      <template v-if="view === 'tools'">
        <header><div><p class="eyebrow">CONTROL ROOM / TOOL REGISTRY</p><h1>工具目录</h1><p class="sub">统一查看 MCP Server 暴露给智能体的业务能力。</p></div><div class="actions"><button @click="showForm = !showForm">{{ showForm ? '取消注册' : '+ 注册工具' }}</button><button @click="loadTools">刷新目录 ↻</button></div></header>
        <form v-if="showForm" class="register-form" @submit.prevent="registerTool"><input v-model="form.toolName" required placeholder="工具名称，如 create_ticket"><input v-model="form.serverName" required placeholder="MCP Server，如 ticket-server"><input v-model="form.description" placeholder="工具描述"><button type="submit">保存工具</button></form>
        <div class="stats"><div><span>已注册工具</span><strong>{{ tools.length }}</strong></div><div><span>当前启用</span><strong>{{ active }}</strong></div><div><span>连接状态</span><strong class="online">{{ error ? 'OFFLINE' : 'ONLINE' }}</strong></div></div>
        <div v-if="loading" class="empty">正在读取工具注册中心…</div>
        <div v-else-if="error" class="empty danger">{{ error }}<button @click="loadTools">重试</button></div>
        <div v-else class="tool-grid"><article v-for="tool in tools" :key="tool.id" class="tool-card"><div class="card-top"><span class="tool-id">TOOL / {{ String(tool.id).padStart(2, '0') }}</span><i :class="['dot', tool.enabled === 1 ? 'on' : 'off']"></i></div><h2>{{ tool.toolName }}</h2><p>{{ tool.description }}</p><div class="server">↳ {{ tool.serverName }} <span>{{ tool.enabled === 1 ? '已启用' : '已停用' }}</span></div><button class="toggle" @click="toggleTool(tool)">{{ tool.enabled === 1 ? '停用工具' : '启用工具' }}</button></article></div>
      </template>
      <template v-else>
        <header><div><p class="eyebrow">CONTROL ROOM / KNOWLEDGE BASE</p><h1>知识库</h1><p class="sub">管理 RAG 知识文档，切片入库后供智能体检索回答。</p></div><div class="actions"><button @click="kbShowForm = !kbShowForm">{{ kbShowForm ? '取消添加' : '+ 添加文档' }}</button><button @click="loadKnowledge">刷新目录 ↻</button></div></header>
        <form v-if="kbShowForm" class="register-form" @submit.prevent="addDocument"><input v-model="kbForm.documentId" required placeholder="文档 ID，如 return-policy"><input v-model="kbForm.tenantId" required placeholder="租户 ID，如 default"><textarea v-model="kbForm.content" required placeholder="文档内容，保存后自动切片入库" rows="3"></textarea><button type="submit">保存文档</button></form>
        <div class="stats"><div><span>知识文档</span><strong>{{ docs.length }}</strong></div><div><span>切片总数</span><strong>{{ totalChunks }}</strong></div><div><span>连接状态</span><strong class="online">{{ kbError ? 'OFFLINE' : 'ONLINE' }}</strong></div></div>
        <div v-if="kbLoading" class="empty">正在读取知识库…</div>
        <div v-else-if="kbError" class="empty danger">{{ kbError }}<button @click="loadKnowledge">重试</button></div>
        <div v-else class="tool-grid"><article v-for="doc in docs" :key="doc.document_id" class="tool-card"><div class="card-top"><span class="tool-id">DOC / {{ doc.document_id }}</span><i class="dot on"></i></div><h2>{{ doc.document_id }}</h2><p>所属租户：{{ doc.tenant_id }}</p><div class="server">↳ {{ doc.chunk_count }} 个切片 <span>已入库</span></div></article></div>
      </template>
    </section>
  </main>
</template>

<style>
:root{font-family:'Manrope','Space Grotesk',sans-serif;color:#17345a!important;background:#edf5ff!important;--line:#d4e4f6;--muted:#6c83a0;--blue:#287be0;--cyan:#18a9d2;--good:#159b67}
body{background:radial-gradient(circle at 82% -12%,#cfe7ff 0,#edf5ff 42%)!important;min-height:100vh}
.rail{background:rgba(255,255,255,.8);border-color:#d8e7f6;backdrop-filter:blur(16px);box-shadow:8px 0 30px #4779a00d}.mark{border-radius:13px;background:linear-gradient(135deg,#76dfff,#287be0);box-shadow:0 10px 28px #287be044}.rail-label{color:#17345a}.rail nav a{border-radius:11px;color:#7890ad}.rail nav .selected{color:#1764bd;background:#e4f1ff;box-shadow:inset 3px 0 var(--blue)}
.content{padding-bottom:70px}.eyebrow{color:var(--blue)}h1{color:#15345b}.sub{color:#6c83a0}
button{border-color:#aacbea;background:#fff;color:#2870c5;border-radius:10px;transition:.2s ease;box-shadow:0 5px 15px #397db31a}button:hover{background:#287be0;border-color:#287be0;color:#fff;transform:translateY(-1px)}
.stats{gap:14px}.stats div{background:rgba(255,255,255,.86);border-color:#d4e4f6;border-radius:15px;box-shadow:0 12px 30px #397db31a}.stats span{color:#7890ad}.stats strong{color:#173b66}.online{color:var(--good)}
.tool-card{background:rgba(255,255,255,.9);border-color:#d4e4f6;border-radius:17px;box-shadow:0 14px 34px #397db31a;transition:.22s ease}.tool-card:hover{transform:translateY(-4px);border-color:#8dbbea;box-shadow:0 18px 42px #397db333}.tool-card h2{color:#173b66}.tool-card p{color:#6c83a0}.server{color:#168eb5}.dot.on{background:var(--good);box-shadow:0 0 14px #159b6744}.tool-id{color:#7392b5}
.toggle{margin-top:18px;padding:8px 12px;font-size:11px}
.shell,.content{background:transparent!important}.rail{background:#f8fbff!important;border-right:1px solid #d4e4f6!important}.rail-label,.rail-label span,.rail-foot{color:#6c83a0!important}.rail nav a{color:#7890ad!important}.rail nav .selected{color:#1764bd!important;background:#e4f1ff!important}.mark{background:linear-gradient(135deg,#76dfff,#287be0)!important;color:#071a35!important}.stats div,.tool-card,.register-form{background:#fff!important;border-color:#d4e4f6!important}.tool-card h2,.stats strong{color:#173b66!important}.tool-card p,.stats span,.sub{color:#6c83a0!important}.server{color:#168eb5!important}.tool-id{color:#7392b5!important}.empty{color:#6c83a0!important}
.actions button,.tool-card button,.register-form button{background:#287be0!important;border:1px solid #287be0!important;color:#fff!important;border-radius:10px!important}.actions button:hover,.tool-card button:hover,.register-form button:hover{background:#1764bd!important;border-color:#1764bd!important;color:#fff!important}.actions button:focus-visible,.tool-card button:focus-visible,.register-form button:focus-visible{outline:3px solid #76dfff!important;outline-offset:2px}
.danger button{background:#287be0!important;border:1px solid #287be0!important;color:#fff!important;border-radius:10px!important}.danger button:hover{background:#1764bd!important;border-color:#1764bd!important;color:#fff!important}
.actions{display:flex;gap:10px}.register-form{display:grid;grid-template-columns:1fr 1fr 1.4fr auto;gap:10px;margin:28px 0 10px;padding:16px;background:#fff;border:1px solid #d4e4f6;border-radius:15px;box-shadow:0 10px 24px #397db31a}.register-form input{border:1px solid #d4e4f6;border-radius:9px;padding:11px 12px;color:#17345a;font:13px Manrope,sans-serif;outline:none}.register-form input:focus{border-color:#54a8ff;box-shadow:0 0 0 3px #54a8ff22}@media(max-width:800px){.register-form{grid-template-columns:1fr}.actions{margin-top:20px}}
.rail nav a{cursor:pointer}.register-form textarea{grid-column:1/-1;border:1px solid #d4e4f6;border-radius:9px;padding:11px 12px;color:#17345a;font:13px Manrope,sans-serif;outline:none;resize:vertical;background:#fff}.register-form textarea:focus{border-color:#54a8ff;box-shadow:0 0 0 3px #54a8ff22}
@media(max-width:800px){.register-form textarea{grid-column:auto}}
</style>
