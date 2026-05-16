<template>
  <div>
    <PageHeader title="环境配置" subtitle="配置 Redis 连接环境和地址补全使用的模型" />

    <nav class="env-tabs" aria-label="环境配置类型">
      <button
        v-for="tabItem in envTabs"
        :key="tabItem.key"
        type="button"
        class="env-tab"
        :class="{ active: activeEnvTab === tabItem.key }"
        @click="activeEnvTab = tabItem.key"
      >
        <span>{{ tabItem.label }}</span>
        <small>{{ tabItem.summary }}</small>
      </button>
    </nav>

    <div v-if="activeEnvTab === 'redis' && redisStatus && !redisStatus.available" class="redis-warning">
      <strong>Redis 未连接</strong>
      <span>{{ redisStatus.message }}</span>
    </div>

    <section v-if="activeEnvTab === 'redis'" class="card section-card environment-card">
      <div class="env-heading">
        <div>
          <h2>Redis 配置</h2>
          <p>可维护多组 Redis 服务器，并选择一组激活给拆分缓存与记录查询使用。</p>
        </div>
        <span class="env-badge">{{ activeRedisLabel }}</span>
      </div>

      <div class="active-redis-banner" :class="activeRedis?.mode ?? 'disabled'">
        <span class="active-pulse" />
        <div>
          <strong>当前激活：{{ activeRedisLabel }}</strong>
          <p v-if="activeRedis">{{ redisAddressLabel(activeRedis) }}</p>
          <p v-else>尚未激活 Redis 配置</p>
          <small>保存配置不会立即切换，点击“激活使用当前 Redis”后才会切换后端实际使用的 Redis。</small>
        </div>
      </div>

      <div class="model-layout">
        <div class="model-editor">
          <div class="model-editor-head">
            <h3>{{ redisForm.id ? '编辑 Redis 配置' : '新增 Redis 配置' }}</h3>
            <button type="button" class="ghost-button" @click="newRedisConfig">新增配置</button>
          </div>

          <div class="env-form model-form">
            <label>
              <span class="field-label">Host</span>
              <input v-model="redisForm.host" class="input" placeholder="127.0.0.1" />
            </label>

            <label>
              <span class="field-label">Port</span>
              <input v-model.number="redisForm.port" class="input" min="1" max="65535" type="number" />
            </label>

            <label>
              <span class="field-label">DB</span>
              <input v-model.number="redisForm.db" class="input" min="0" type="number" />
            </label>

            <label>
              <span class="field-label">Password</span>
              <input v-model="redisForm.password" class="input" placeholder="无密码可留空" type="password" />
            </label>
          </div>

          <div class="model-feedback">
            <div v-if="message" class="env-message" :class="{ success: testOk, danger: !testOk }">
              <span class="message-dot" />
              <span>{{ message }}</span>
            </div>
            <div v-else class="env-message-placeholder">先测试连接，通过后可激活当前 Redis</div>
          </div>

          <div class="env-actions model-actions">
            <button type="button" class="secondary-button" :disabled="loading || testing || saving" @click="testConfig">
              {{ testing ? '测试中…' : '测试连接' }}
            </button>
            <button type="button" class="ghost-button" :disabled="loading || saving || testing" @click="saveConfig">
              {{ saving ? '保存中…' : '保存配置' }}
            </button>
            <button type="button" class="primary-button" :disabled="(!redisForm.id && !redisLastTestOk) || activatingRedis" @click="activateCurrentRedis">
              {{ activatingRedis ? '激活中…' : '激活使用当前 Redis' }}
            </button>
          </div>
        </div>

        <div class="model-groups">
          <div v-if="!redisGroups.length" class="model-empty">暂无 Redis 配置，请先新增一组。</div>
          <section v-for="group in redisGroups" :key="group.mode" class="model-group">
            <h3>{{ group.label }}</h3>
            <div
              v-for="item in group.configs"
              :key="item.id"
              class="model-row"
              :class="{ active: item.active, selected: item.id === redisForm.id }"
            >
              <button type="button" class="model-select-button" @click="selectRedisConfig(item)">
                <strong>{{ redisAddressLabel(item) }}</strong>
                <span>{{ redisModeLabel(item.mode) }}</span>
              </button>
              <div class="model-row-actions">
                <span v-if="item.active" class="model-active-pill">使用中</span>
                <button type="button" class="action-link" @click="selectRedisConfig(item)">
                  {{ item.id === redisForm.id ? '已选择' : '选择' }}
                </button>
                <button type="button" class="action-link" :disabled="testing" @click="runSavedRedisTest(item)">
                  测试
                </button>
                <button v-if="!item.active" type="button" class="action-link" :disabled="activatingRedis" @click="activateSavedRedis(item)">
                  激活
                </button>
                <button type="button" class="action-link danger" @click="removeRedisConfig(item)">删除</button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </section>

    <section v-if="activeEnvTab === 'model'" class="card section-card environment-card">
      <div class="env-heading">
        <div>
          <h2>模型配置</h2>
          <p>模型接口只支持 OpenAI Chat Completions 兼容格式。可按提供商维护多组模型，并选择一组激活给地址补全使用。</p>
        </div>
        <span class="env-badge">{{ activeModelLabel }}</span>
      </div>

      <div class="active-redis-banner model-banner" :class="{ disabled: !activeModel }">
        <span class="active-pulse" />
        <div>
          <strong>当前激活：{{ activeModelLabel }}</strong>
          <p v-if="activeModel">{{ activeModel.provider }} / {{ activeModel.model }}</p>
          <p v-else>尚未激活模型配置</p>
          <small>只有测试运行通过的配置才能激活。激活后，地址补全服务会优先使用当前模型。</small>
        </div>
      </div>

      <div class="model-layout">
        <div class="model-editor">
          <div class="model-editor-head">
            <h3>{{ modelForm.id ? '编辑模型配置' : '新增模型配置' }}</h3>
            <button type="button" class="ghost-button" @click="newModelConfig">新增配置</button>
          </div>

          <div class="env-form model-form">
            <label>
              <span class="field-label">提供商</span>
              <input v-model="modelForm.provider" class="input" placeholder="例如：小米 / DeepSeek" />
            </label>

            <label>
              <span class="field-label">Base URL</span>
              <input v-model="modelForm.baseUrl" class="input" placeholder="https://api.example.com/v1" />
            </label>

            <label>
              <span class="field-label">API Key</span>
              <input v-model="modelForm.apiKey" class="input" placeholder="请输入 API Key" type="password" autocomplete="off" />
            </label>

            <label>
              <span class="field-label">Model</span>
              <input v-model="modelForm.model" class="input" placeholder="例如：deepseek-chat" />
            </label>
          </div>

          <div class="model-feedback">
            <div v-if="modelMessage" class="env-message" :class="{ success: modelOk, danger: !modelOk }">
              <span class="message-dot" />
              <span>{{ modelMessage }}</span>
            </div>
            <div v-else class="env-message-placeholder">先测试运行，通过后可激活当前模型</div>
          </div>

          <div class="env-actions model-actions">
            <button type="button" class="secondary-button" :disabled="modelTesting || modelSaving" @click="runModelTest">
              {{ modelTesting ? '测试中…' : '测试运行' }}
            </button>
            <button type="button" class="ghost-button" :disabled="modelSaving || modelTesting" @click="saveCurrentModel">
              {{ modelSaving ? '保存中…' : '保存配置' }}
            </button>
            <button type="button" class="primary-button" :disabled="!modelLastTestOk || modelActivating" @click="activateCurrentModel">
              {{ modelActivating ? '激活中…' : '激活使用当前模型' }}
            </button>
          </div>
        </div>

        <div class="model-groups">
          <div v-if="!modelGroups.length" class="model-empty">暂无模型配置，请先新增一组。</div>
          <section v-for="group in modelGroups" :key="group.provider" class="model-group">
            <h3>{{ group.provider }}</h3>
            <div
              v-for="item in group.models"
              :key="item.id"
              class="model-row"
              :class="{ active: item.active, selected: item.id === modelForm.id }"
            >
              <button type="button" class="model-select-button" @click="selectModelConfig(item)">
                <strong>{{ item.model }}</strong>
                <span>{{ item.baseUrl }}</span>
              </button>
              <div class="model-row-actions">
                <span v-if="item.active" class="model-active-pill">使用中</span>
                <button type="button" class="action-link" @click="selectModelConfig(item)">
                  {{ item.id === modelForm.id ? '已选择' : '选择' }}
                </button>
                <button type="button" class="action-link" :disabled="modelTesting" @click="runSavedModelTest(item)">
                  测试
                </button>
                <button v-if="!item.active" type="button" class="action-link" :disabled="modelActivating" @click="activateSavedModel(item)">
                  激活
                </button>
                <button type="button" class="action-link danger" @click="removeModelConfig(item)">删除</button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </section>

    <div v-if="message" class="env-toast" :class="{ success: testOk, danger: !testOk }">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  activateModelConfig,
  activateRedisConfig,
  deleteModelConfig,
  deleteRedisConfig,
  getModelConfigs,
  getRedisConfigs,
  getRedisStatus,
  saveModelConfig,
  saveRedisConfigProfile,
  testModelConfig,
  type ModelConfig,
  testRedisConfig,
  type RedisConfig,
  type RedisStatusResponse,
} from '../api/address'
import PageHeader from '../components/PageHeader.vue'

type EnvTabKey = 'redis' | 'model'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const activatingRedis = ref(false)
const testOk = ref(false)
const message = ref('')
const redisStatus = ref<RedisStatusResponse | null>(null)
const redisConfigs = ref<RedisConfig[]>([])
const redisActiveId = ref('')
const redisLastTestOk = ref(false)
const testedRedisIds = ref<string[]>([])
const modelConfigs = ref<ModelConfig[]>([])
const modelActiveId = ref('')
const modelSaving = ref(false)
const modelTesting = ref(false)
const modelActivating = ref(false)
const modelLastTestOk = ref(false)
const modelOk = ref(false)
const modelMessage = ref('')
const testedModelIds = ref<string[]>([])
const activeEnvTab = ref<EnvTabKey>('redis')
let toastTimer: number | undefined

const envTabs: Array<{ key: EnvTabKey; label: string; summary: string }> = [
  { key: 'redis', label: 'Redis 配置', summary: '缓存与记录查询' },
  { key: 'model', label: '模型配置', summary: '地址补全模型' },
]

const redisForm = reactive<RedisConfig>({
  id: '',
  mode: 'local',
  host: '127.0.0.1',
  port: 6379,
  db: 0,
  password: '',
  updatedAt: '',
})

const modelForm = reactive<ModelConfig>({
  id: '',
  provider: '',
  baseUrl: '',
  apiKey: '',
  model: '',
})

const redisModeLabel = (mode: RedisConfig['mode']) => {
  if (mode === 'remote') {
    return '远程 Redis'
  }
  if (mode === 'disabled') {
    return '未连接 Redis'
  }
  return 'Redis'
}

const redisAddressLabel = (config: RedisConfig) => {
  if (config.mode === 'disabled') {
    return '未连接 Redis'
  }
  return `${config.host || '未填写 Host'}:${config.port || '-'} / DB ${config.db ?? 0}`
}

const activeRedis = computed(() => redisConfigs.value.find((item) => item.id === redisActiveId.value))

const activeRedisLabel = computed(() => {
  if (!activeRedis.value) {
    return '未激活 Redis'
  }
  return activeRedis.value.mode === 'disabled' ? '未连接 Redis' : redisAddressLabel(activeRedis.value)
})

const redisGroups = computed(() => {
  const groups = new Map<RedisConfig['mode'], RedisConfig[]>()
  for (const item of redisConfigs.value.filter((config) => config.mode !== 'disabled')) {
    groups.set(item.mode, [...(groups.get(item.mode) ?? []), item])
  }
  return Array.from(groups.entries()).map(([mode, configs]) => ({
    mode,
    label: redisModeLabel(mode),
    configs,
  }))
})

const activeModel = computed(() => modelConfigs.value.find((item) => item.id === modelActiveId.value))

const activeModelLabel = computed(() => {
  if (!activeModel.value) {
    return '未激活模型'
  }
  return `${activeModel.value.provider} / ${activeModel.value.model}`
})

const modelGroups = computed(() => {
  const groups = new Map<string, ModelConfig[]>()
  for (const item of modelConfigs.value) {
    const provider = item.provider || '未命名提供商'
    groups.set(provider, [...(groups.get(provider) ?? []), item])
  }
  return Array.from(groups.entries()).map(([provider, models]) => ({ provider, models }))
})

const inferMode = (host: string): RedisConfig['mode'] => {
  const normalizedHost = host.trim().toLowerCase()
  return normalizedHost === '127.0.0.1' || normalizedHost === 'localhost' ? 'local' : 'remote'
}

const redisPayload = (): RedisConfig => ({
  ...redisForm,
  id: redisForm.id || undefined,
  host: redisForm.host.trim(),
  port: Number(redisForm.port),
  db: Number(redisForm.db),
  password: redisForm.password ?? '',
  mode: redisForm.mode === 'disabled' ? 'disabled' : inferMode(redisForm.host),
})

const applyRedisForm = (config?: RedisConfig) => {
  redisForm.id = config?.id ?? ''
  redisForm.mode = config?.mode ?? 'local'
  redisForm.host = config?.host ?? '127.0.0.1'
  redisForm.port = config?.port ?? 6379
  redisForm.db = config?.db ?? 0
  redisForm.password = config?.password ?? ''
  redisForm.updatedAt = config?.updatedAt ?? ''
  redisLastTestOk.value = false
}

const validate = () => {
  if (!redisForm.host.trim()) {
    return 'Host 不能为空'
  }
  if (!Number.isInteger(Number(redisForm.port)) || Number(redisForm.port) < 1 || Number(redisForm.port) > 65535) {
    return 'Port 必须在 1 到 65535 之间'
  }
  if (!Number.isInteger(Number(redisForm.db)) || Number(redisForm.db) < 0) {
    return 'DB 必须是大于等于 0 的整数'
  }
  return ''
}

const showMessage = (text: string, ok: boolean) => {
  testOk.value = ok
  message.value = text
  if (toastTimer !== undefined) {
    window.clearTimeout(toastTimer)
  }
  toastTimer = window.setTimeout(() => {
    message.value = ''
    toastTimer = undefined
  }, 5000)
}

const loadConfig = async (notify = false) => {
  loading.value = true
  try {
    const result = await getRedisConfigs()
    redisActiveId.value = result.activeId
    redisConfigs.value = result.configs
    const selected = result.configs.find((item) => item.id === redisForm.id)
    applyRedisForm(selected ?? result.configs.find((item) => item.id === result.activeId) ?? result.configs[0])
    if (notify) {
      showMessage('Redis 配置已重置为当前列表值', true)
    }
  } catch (error) {
    showMessage(error instanceof Error ? error.message : '读取 Redis 配置失败', false)
  } finally {
    loading.value = false
  }
}

const loadRedisStatus = async () => {
  try {
    redisStatus.value = await getRedisStatus()
  } catch {
    redisStatus.value = {
      available: false,
      mode: activeRedis.value?.mode ?? 'disabled',
      host: activeRedis.value?.host ?? '127.0.0.1',
      port: activeRedis.value?.port ?? 6379,
      db: activeRedis.value?.db ?? 0,
      message: '当前未连接 Redis，系统将使用本地模式运行；如需跨任务缓存和高性能记录查询，请安装或配置 Redis。',
    }
  }
}

const newRedisConfig = () => {
  applyRedisForm()
  message.value = ''
}

const testConfig = async () => {
  const error = validate()
  if (error) {
    showMessage(error, false)
    return
  }

  testing.value = true
  try {
    const result = await testRedisConfig(redisPayload())
    redisLastTestOk.value = result.ok
    if (result.ok && redisForm.id && !testedRedisIds.value.includes(redisForm.id)) {
      testedRedisIds.value = [...testedRedisIds.value, redisForm.id]
    }
    showMessage(result.message, result.ok)
    await loadRedisStatus()
  } catch (err) {
    showMessage(err instanceof Error ? err.message : 'Redis 连接测试失败', false)
  } finally {
    testing.value = false
  }
}

const saveConfig = async () => {
  const error = validate()
  if (error) {
    showMessage(error, false)
    return
  }

  saving.value = true
  const wasTested = redisLastTestOk.value
  try {
    const saved = await saveRedisConfigProfile(redisPayload())
    redisForm.id = saved.id
    await loadConfig()
    redisLastTestOk.value = wasTested
    if (wasTested && saved.id && !testedRedisIds.value.includes(saved.id)) {
      testedRedisIds.value = [...testedRedisIds.value, saved.id]
    }
    showMessage('Redis 配置已保存', true)
    return saved
  } catch (err) {
    showMessage(err instanceof Error ? err.message : '保存 Redis 配置失败', false)
    return null
  } finally {
    saving.value = false
  }
}

const selectRedisConfig = (config: RedisConfig) => {
  applyRedisForm(config)
  message.value = ''
}

const runSavedRedisTest = async (config: RedisConfig) => {
  selectRedisConfig(config)
  await testConfig()
}

const activateCurrentRedis = async () => {
  if (!redisForm.id && !redisLastTestOk.value) return
  activatingRedis.value = true
  try {
    let targetId = redisForm.id
    if (!targetId) {
      const saved = await saveConfig()
      targetId = saved?.id ?? ''
    }
    if (!targetId) return
    const result = await activateRedisConfig(targetId)
    redisActiveId.value = result.activeId
    await loadConfig()
    await loadRedisStatus()
    showMessage('当前 Redis 已激活，后端将使用该配置', true)
  } catch (err) {
    showMessage(err instanceof Error ? err.message : '激活 Redis 失败', false)
  } finally {
    activatingRedis.value = false
  }
}

const activateSavedRedis = async (config: RedisConfig) => {
  if (!config.id) return
  selectRedisConfig(config)
  activatingRedis.value = true
  try {
    const result = await activateRedisConfig(config.id)
    redisActiveId.value = result.activeId
    await loadConfig()
    await loadRedisStatus()
    showMessage('当前 Redis 已激活，后端将使用该配置', true)
  } catch (err) {
    showMessage(err instanceof Error ? err.message : '激活 Redis 失败', false)
  } finally {
    activatingRedis.value = false
  }
}

const removeRedisConfig = async (config: RedisConfig) => {
  if (!config.id) return
  try {
    await deleteRedisConfig(config.id)
    if (redisForm.id === config.id) {
      newRedisConfig()
    }
    await loadConfig()
    await loadRedisStatus()
    showMessage('Redis 配置已删除', true)
  } catch (err) {
    showMessage(err instanceof Error ? err.message : '删除 Redis 配置失败', false)
  }
}

const resetModelTestState = () => {
  modelLastTestOk.value = false
  modelOk.value = false
  modelMessage.value = ''
}

const validateModel = () => {
  if (!modelForm.provider?.trim()) return '提供商不能为空'
  if (!modelForm.baseUrl?.trim()) return 'Base URL 不能为空'
  if (!modelForm.apiKey?.trim()) return 'API Key 不能为空'
  if (!modelForm.model?.trim()) return 'Model 不能为空'
  return ''
}

const modelPayload = (): ModelConfig => ({
  id: modelForm.id || undefined,
  provider: modelForm.provider.trim(),
  baseUrl: modelForm.baseUrl.trim(),
  apiKey: modelForm.apiKey.trim(),
  model: modelForm.model.trim(),
})

const loadModelConfigs = async () => {
  try {
    const result = await getModelConfigs()
    modelActiveId.value = result.activeId
    modelConfigs.value = result.models
  } catch (error) {
    modelMessage.value = error instanceof Error ? error.message : '读取模型配置失败'
    modelOk.value = false
  }
}

const applyModelForm = (config?: ModelConfig) => {
  modelForm.id = config?.id ?? ''
  modelForm.provider = config?.provider ?? ''
  modelForm.baseUrl = config?.baseUrl ?? ''
  modelForm.apiKey = config?.apiKey ?? ''
  modelForm.model = config?.model ?? ''
  resetModelTestState()
}

const newModelConfig = () => {
  applyModelForm()
}

const selectModelConfig = (config: ModelConfig) => {
  applyModelForm(config)
}

const saveCurrentModel = async () => {
  const error = validateModel()
  if (error) {
    modelMessage.value = error
    modelOk.value = false
    return null
  }
  modelSaving.value = true
  try {
    const saved = await saveModelConfig(modelPayload())
    modelForm.id = saved.id
    await loadModelConfigs()
    modelMessage.value = '模型配置已保存'
    modelOk.value = true
    return saved
  } catch (error) {
    modelMessage.value = error instanceof Error ? error.message : '保存模型配置失败'
    modelOk.value = false
    return null
  } finally {
    modelSaving.value = false
  }
}

const runModelTest = async () => {
  const error = validateModel()
  if (error) {
    modelMessage.value = error
    modelOk.value = false
    modelLastTestOk.value = false
    return
  }
  modelTesting.value = true
  try {
    const result = await testModelConfig(modelPayload())
    modelMessage.value = result.message
    modelOk.value = result.ok
    modelLastTestOk.value = result.ok
    if (result.ok && modelForm.id && !testedModelIds.value.includes(modelForm.id)) {
      testedModelIds.value = [...testedModelIds.value, modelForm.id]
    }
  } catch (error) {
    modelMessage.value = error instanceof Error ? error.message : '模型测试失败'
    modelOk.value = false
    modelLastTestOk.value = false
  } finally {
    modelTesting.value = false
  }
}

const runSavedModelTest = async (config: ModelConfig) => {
  selectModelConfig(config)
  await runModelTest()
}

const activateCurrentModel = async () => {
  if (!modelLastTestOk.value) return
  modelActivating.value = true
  try {
    let targetId = modelForm.id
    if (!targetId) {
      const saved = await saveCurrentModel()
      targetId = saved?.id ?? ''
    }
    if (!targetId) {
      return
    }
    const result = await activateModelConfig(targetId)
    modelActiveId.value = result.activeId
    await loadModelConfigs()
    modelMessage.value = '当前模型已激活，地址补全将使用该配置'
    modelOk.value = true
  } catch (error) {
    modelMessage.value = error instanceof Error ? error.message : '激活模型失败'
    modelOk.value = false
  } finally {
    modelActivating.value = false
  }
}

const activateSavedModel = async (config: ModelConfig) => {
  if (!config.id) return
  selectModelConfig(config)
  if (!testedModelIds.value.includes(config.id)) {
    modelMessage.value = '请先测试运行该模型，通过后再激活'
    modelOk.value = false
    return
  }
  modelActivating.value = true
  try {
    const result = await activateModelConfig(config.id)
    modelActiveId.value = result.activeId
    await loadModelConfigs()
    modelMessage.value = '当前模型已激活，地址补全将使用该配置'
    modelOk.value = true
  } catch (error) {
    modelMessage.value = error instanceof Error ? error.message : '激活模型失败'
    modelOk.value = false
  } finally {
    modelActivating.value = false
  }
}

const removeModelConfig = async (config: ModelConfig) => {
  if (!config.id) return
  try {
    await deleteModelConfig(config.id)
    if (modelForm.id === config.id) {
      newModelConfig()
    }
    await loadModelConfigs()
    modelMessage.value = '模型配置已删除'
    modelOk.value = true
  } catch (error) {
    modelMessage.value = error instanceof Error ? error.message : '删除模型配置失败'
    modelOk.value = false
  }
}

watch(
  () => `${redisForm.host}|${redisForm.port}|${redisForm.db}|${redisForm.password}`,
  () => {
    redisLastTestOk.value = false
  },
)

watch(
  () => `${modelForm.provider}|${modelForm.baseUrl}|${modelForm.apiKey}|${modelForm.model}`,
  () => {
    modelLastTestOk.value = false
  },
)

onMounted(async () => {
  await loadConfig()
  await loadRedisStatus()
  await loadModelConfigs()
})
</script>

<style scoped>
.environment-card {
  width: 100%;
  box-sizing: border-box;
}

.env-tabs {
  display: flex;
  gap: 10px;
  margin: 0 0 16px;
  padding: 6px;
  width: fit-content;
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #f8fbff;
  overflow-x: auto;
}

.env-tab {
  display: grid;
  gap: 2px;
  min-width: 168px;
  padding: 12px 16px;
  border: 1px solid transparent;
  border-radius: 10px;
  color: var(--text-sub);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.env-tab span {
  color: var(--ink);
  font-weight: 800;
}

.env-tab small {
  color: var(--text-muted);
  font-size: 12px;
}

.env-tab.active {
  border-color: rgba(37, 99, 235, 0.28);
  background: #fff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.08);
}

.env-tab.active span {
  color: #0f5bd7;
}

.env-heading {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 24px;
}

.env-heading h2 {
  margin: 0;
  font-size: 22px;
}

.env-heading p {
  margin: 8px 0 0;
  color: var(--text-sub);
}

.env-badge {
  padding: 8px 12px;
  border-radius: 999px;
  color: #0f5bd7;
  background: #edf4ff;
  font-weight: 700;
}

.active-redis-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
  padding: 14px 16px;
  border: 1px solid rgba(31, 120, 255, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
}

.active-redis-banner.remote {
  border-color: rgba(245, 158, 11, 0.28);
  background: linear-gradient(180deg, #fffdf7 0%, #fff7e6 100%);
}

.active-redis-banner.disabled {
  border-color: rgba(148, 163, 184, 0.35);
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

.active-redis-banner strong {
  color: #0f172a;
}

.active-redis-banner p {
  margin: 4px 0 0;
  color: var(--text-sub);
  font-size: 14px;
}

.active-redis-banner small {
  display: block;
  margin-top: 6px;
  color: #b45309;
  font-weight: 700;
}

.active-pulse {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: var(--success);
  box-shadow: 0 0 0 7px rgba(16, 185, 129, 0.12);
  flex: none;
}

.active-redis-banner.disabled .active-pulse {
  background: #94a3b8;
  box-shadow: 0 0 0 7px rgba(148, 163, 184, 0.16);
}

.model-banner {
  border-color: rgba(37, 99, 235, 0.2);
}

.env-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 18px;
}

.env-form label {
  display: grid;
  gap: 8px;
}

.env-message {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin-right: auto;
  font-weight: 700;
}

.env-message.success {
  color: var(--success);
}

.env-message.danger {
  color: var(--danger);
}

.message-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: currentColor;
  flex: none;
}

.env-message-placeholder {
  margin-right: auto;
  color: var(--text-muted);
  font-size: 14px;
}

.env-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}

.env-toast {
  position: fixed;
  right: 28px;
  top: 24px;
  z-index: 100;
  max-width: min(420px, calc(100vw - 56px));
  padding: 14px 18px;
  border-radius: 14px;
  color: #0f172a;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.16);
  font-weight: 700;
}

.env-toast.success {
  color: #047857;
  border-color: rgba(16, 185, 129, 0.35);
  background: #ecfdf5;
}

.env-toast.danger {
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.35);
  background: #fef2f2;
}

.danger-button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  color: #b91c1c;
  border: 1px solid #fecaca;
  background: #fff5f5;
  font-weight: 700;
  cursor: pointer;
}

.danger-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.redis-warning {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  color: #9a3412;
  background: #fff7ed;
}

.redis-warning strong {
  flex: none;
}

.model-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  gap: 22px;
  align-items: start;
}

.model-editor {
  min-width: 0;
}

.model-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.model-editor-head h3,
.model-group h3 {
  margin: 0;
  color: var(--ink);
  font-size: 17px;
}

.model-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.model-feedback {
  min-height: 24px;
  margin-top: 18px;
}

.model-feedback .env-message,
.model-feedback .env-message-placeholder {
  margin-right: 0;
}

.model-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
  justify-content: stretch;
  margin-top: 12px;
}

.model-actions .secondary-button,
.model-actions .ghost-button,
.model-actions .primary-button {
  width: 100%;
  min-width: 0;
  padding-inline: 12px;
}

.model-groups {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.model-empty {
  padding: 20px;
  border: 1px dashed var(--border-strong);
  border-radius: 14px;
  color: var(--text-muted);
  background: #f8fafc;
  text-align: center;
  font-weight: 700;
}

.model-group {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #f8fbff;
}

.model-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: #fff;
}

.model-row:hover,
.model-row.selected {
  border-color: rgba(37, 99, 235, 0.3);
  background: #f8fbff;
}

.model-row.selected {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.model-row.active {
  border-color: rgba(16, 185, 129, 0.34);
  background: #ecfdf5;
}

.model-select-button {
  display: block;
  min-width: 0;
  flex: 1;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.model-row strong,
.model-row span {
  display: block;
}

.model-row strong {
  color: var(--ink);
  font-size: 15px;
}

.model-row span {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.model-row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex: none;
  flex-wrap: wrap;
  max-width: 260px;
}

.model-active-pill {
  padding: 4px 8px;
  border-radius: 999px;
  color: #047857 !important;
  background: #d1fae5;
  font-size: 12px !important;
  font-weight: 800;
}

@media (max-width: 1280px) {
  .env-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .model-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .env-heading,
  .redis-warning {
    flex-direction: column;
  }

  .env-tabs {
    width: 100%;
  }

  .env-tab {
    min-width: 150px;
  }

  .env-form {
    grid-template-columns: 1fr;
  }

  .model-form {
    grid-template-columns: 1fr;
  }

  .env-actions {
    align-items: stretch;
  }

  .env-actions button {
    flex: 1 1 140px;
  }

  .model-actions {
    grid-template-columns: 1fr;
  }
}
</style>
