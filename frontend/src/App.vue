<script setup>
import { computed, onMounted, ref } from 'vue'

const tools = ref([])
const loading = ref(true)
const error = ref('')
const active = computed(() => tools.value.filter(item => item.enabled === 1).length)

async function loadTools() {
  loading.value = true
  try {
    const response = await fetch('/api/internal/tools')
    if (!response.ok) throw new Error('工具服务暂不可用')
    tools.value = await response.json()
    error.value = ''
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

onMounted(loadTools)
</script>

<template>
  <main class="shell">
    <aside class="rail"><div class="mark">HZ</div><div class="rail-label">汇智通<br><span>AI CONTROL</span></div><nav><a class="selected">工具目录</a><a>智能体</a><a>知识库</a><a>调用审计</a></nav><div class="rail-foot">LOCAL / DEV</div></aside>
    <section class="content">
      <header><div><p class="eyebrow">CONTROL ROOM / TOOL REGISTRY</p><h1>工具目录</h1><p class="sub">统一查看 MCP Server 暴露给智能体的业务能力。</p></div><button @click="loadTools">刷新目录 ↻</button></header>
      <div class="stats"><div><span>已注册工具</span><strong>{{ tools.length }}</strong></div><div><span>当前启用</span><strong>{{ active }}</strong></div><div><span>连接状态</span><strong class="online">{{ error ? 'OFFLINE' : 'ONLINE' }}</strong></div></div>
      <div v-if="loading" class="empty">正在读取工具注册中心…</div>
      <div v-else-if="error" class="empty danger">{{ error }}<button @click="loadTools">重试</button></div>
      <div v-else class="tool-grid"><article v-for="tool in tools" :key="tool.id" class="tool-card"><div class="card-top"><span class="tool-id">TOOL / {{ String(tool.id).padStart(2, '0') }}</span><i :class="['dot', tool.enabled === 1 ? 'on' : 'off']"></i></div><h2>{{ tool.toolName }}</h2><p>{{ tool.description }}</p><div class="server">↳ {{ tool.serverName }} <span>{{ tool.enabled === 1 ? '已启用' : '已停用' }}</span></div></article></div>
    </section>
  </main>
</template>

<style>
:root{font-family:'Manrope','Space Grotesk',sans-serif;color:#e8f0ff;background:#08111f;--line:#213b61;--muted:#8297b5;--blue:#54a8ff;--cyan:#76e4ff;--good:#79e6b2}
body{background:radial-gradient(circle at 82% -12%,#19375e 0,#08111f 38%);min-height:100vh}
.rail{background:rgba(8,17,31,.88);border-color:var(--line);backdrop-filter:blur(16px)}
.mark{border-radius:13px;background:linear-gradient(135deg,var(--cyan),var(--blue));box-shadow:0 10px 28px #227dc755}
.rail nav a{border-radius:11px}.rail nav .selected{color:#fff;background:linear-gradient(90deg,#193a63,#122741);box-shadow:inset 3px 0 var(--blue)}
.content{padding-bottom:70px}.eyebrow{color:var(--blue)}
button{border-color:#428bd6;background:#102948;color:#a9d5ff;border-radius:10px;transition:.2s ease}button:hover{background:#1a4e83;border-color:var(--cyan);color:#fff;transform:translateY(-1px)}
.stats{gap:12px}.stats div{background:linear-gradient(145deg,#122541,#0d1a2d);border-color:var(--line);border-radius:15px;box-shadow:0 12px 30px #0209144d}.online{color:var(--good)}
.tool-card{background:linear-gradient(145deg,#132744cc,#0d1a2ecc);border-color:var(--line);border-radius:17px;box-shadow:0 14px 34px #0209144d;transition:.22s ease}.tool-card:hover{transform:translateY(-4px);border-color:#3e78b8;box-shadow:0 18px 42px #02091488}.tool-card h2{color:#f3f7ff}.tool-card p{color:#9eb1ca}.server{color:var(--cyan)}.dot.on{background:var(--good);box-shadow:0 0 14px #79e6b288}
</style>
