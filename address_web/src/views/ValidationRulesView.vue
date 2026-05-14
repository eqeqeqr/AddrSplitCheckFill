<template>
  <div>
    <PageHeader
      title="自定义校验规则"
      subtitle="管理拆分层级的正则校验规则，命中规则即判定为未通过"
    />

    <section class="card section-card">
      <div class="toolbar rule-toolbar">
        <TabSwitcher v-model="activeTab" :tabs="validationRuleTabs" compact />
        <div class="toolbar-spacer" />
        <input
          ref="importInputRef"
          type="file"
          accept=".xlsx,.xls"
          class="file-input"
          @change="handleImportFile"
        />
        <button type="button" class="secondary-button" :disabled="isImporting" @click="openImport">
          {{ isImporting ? '导入中…' : '批量导入' }}
        </button>
        <button type="button" class="primary-button" @click="openCreate">＋ 新建规则</button>
      </div>

      <template v-if="activeTab === 'rules'">
        <BaseTable :columns="ruleColumns" :rows="rules" row-key="ruleId">
          <template #cell-levels="{ row }">
            <span class="level-list">{{ row.levels.join(';') }}</span>
          </template>
          <template #cell-actions="{ row }">
            <span class="link-group">
              <span class="action-link" @click="openEdit(row)">编辑</span>
              <span class="action-link danger" @click="removeRule(row.ruleId)">删除</span>
            </span>
          </template>
        </BaseTable>

        <p class="rule-note">导入 Excel 表头需依次为：规则ID、正则表达式、校验层级；校验层级示例：level_1;level_2;level_7。</p>
        <p v-if="feedbackMessage" class="success-note">{{ feedbackMessage }}</p>
        <p v-if="errorMessage && !showEditor" class="error-note">{{ errorMessage }}</p>
      </template>

      <div v-else class="regex-test-panel">
        <div class="regex-test-header">
          <div>
            <h3>正则表达式在线测试</h3>
            <p>内嵌菜鸟工具正则测试页，可将校验规则复制到页面中进行匹配验证。</p>
          </div>
          <a class="secondary-button" href="https://www.jyshare.com/front-end/854/" target="_blank" rel="noreferrer">
            新窗口打开
          </a>
        </div>
        <div class="regex-test-frame-wrap">
          <iframe
            class="regex-test-frame"
            src="https://www.jyshare.com/front-end/854/"
            title="正则表达式在线测试"
            referrerpolicy="no-referrer"
          />
        </div>
        <p class="rule-note">如果第三方网站限制嵌入显示，请点击右上角“新窗口打开”。</p>
      </div>
    </section>

    <div v-if="showEditor" class="modal-mask" @click.self="showEditor = false">
      <div class="modal-card rule-modal">
        <div class="modal-body">
          <div class="modal-header">
            <div>
              <h3>{{ editingId ? '编辑校验规则' : '新建校验规则' }}</h3>
              <p>配置规则ID、正则表达式和需要校验的拆分层级。</p>
            </div>
            <button type="button" class="close-button" @click="showEditor = false">×</button>
          </div>

          <div class="rule-form">
            <label>
              <span class="field-label">规则ID</span>
              <input v-model="form.ruleId" class="input" placeholder="请输入规则ID" />
            </label>
            <label class="pattern-field">
              <span class="field-label">正则表达式</span>
              <textarea v-model="form.pattern" class="textarea" placeholder="请输入正则表达式" />
            </label>
            <div class="levels-field">
              <span class="field-label">校验层级</span>
              <div class="levels-grid">
                <label v-for="level in levelOptions" :key="level" class="level-option">
                  <input v-model="form.levels" type="checkbox" :value="level" />
                  <span>{{ level }}</span>
                </label>
              </div>
            </div>
          </div>

          <p v-if="editorError" class="error-note">{{ editorError }}</p>

          <div class="modal-footer">
            <button type="button" class="ghost-button" @click="showEditor = false">取消</button>
            <button type="button" class="primary-button" @click="saveRule">确定</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createValidationRule,
  deleteValidationRule,
  getValidationRuleList,
  importValidationRules,
  updateValidationRule,
} from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import PageHeader from '../components/PageHeader.vue'
import TabSwitcher from '../components/TabSwitcher.vue'
import { validationRuleTabs } from '../mock/data'
import type { TableColumn, ValidationRule } from '../types'

const activeTab = ref('rules')
const rules = ref<ValidationRule[]>([])
const showEditor = ref(false)
const editingId = ref('')
const errorMessage = ref('')
const editorError = ref('')
const feedbackMessage = ref('')
const isImporting = ref(false)
const importInputRef = ref<HTMLInputElement | null>(null)
const levelOptions = Array.from({ length: 11 }, (_, index) => `level_${index + 1}`)
const form = ref({
  ruleId: '',
  pattern: '',
  levels: [] as string[],
})

const ruleColumns: TableColumn[] = [
  { key: 'ruleId', label: '规则ID', width: '160px' },
  { key: 'pattern', label: '正则表达式', width: '430px' },
  { key: 'levels', label: '校验层级', width: '260px' },
  { key: 'actions', label: '操作', width: '140px' },
]

const loadRules = async () => {
  rules.value = await getValidationRuleList()
}

const openCreate = () => {
  feedbackMessage.value = ''
  errorMessage.value = ''
  editorError.value = ''
  editingId.value = ''
  form.value = {
    ruleId: '',
    pattern: '',
    levels: [],
  }
  showEditor.value = true
}

const openEdit = (rule: ValidationRule) => {
  feedbackMessage.value = ''
  errorMessage.value = ''
  editorError.value = ''
  editingId.value = rule.ruleId
  form.value = {
    ruleId: rule.ruleId,
    pattern: rule.pattern,
    levels: [...rule.levels],
  }
  showEditor.value = true
}

const validateForm = () => {
  if (!form.value.ruleId.trim()) {
    return '规则ID不能为空'
  }
  if (!form.value.pattern.trim()) {
    return '正则表达式不能为空'
  }
  if (form.value.levels.length === 0) {
    return '请至少选择一个校验层级'
  }
  return ''
}

const saveRule = async () => {
  editorError.value = validateForm()
  if (editorError.value) {
    return
  }

  const payload = {
    ruleId: form.value.ruleId.trim(),
    pattern: form.value.pattern.trim(),
    levels: form.value.levels,
  }
  try {
    if (editingId.value) {
      await updateValidationRule(editingId.value, payload)
    } else {
      await createValidationRule(payload)
    }
    showEditor.value = false
    await loadRules()
    feedbackMessage.value = '校验规则已保存'
  } catch (error) {
    editorError.value = error instanceof Error ? error.message : '保存失败'
  }
}

const removeRule = async (ruleId: string) => {
  feedbackMessage.value = ''
  errorMessage.value = ''
  if (!window.confirm('确认删除这条校验规则吗？')) {
    return
  }
  try {
    await deleteValidationRule(ruleId)
    await loadRules()
    feedbackMessage.value = '校验规则已删除'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '删除失败'
  }
}

const openImport = () => {
  errorMessage.value = ''
  feedbackMessage.value = ''
  importInputRef.value?.click()
}

const handleImportFile = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }

  isImporting.value = true
  try {
    const result = await importValidationRules(file)
    rules.value = result.rules
    await loadRules()
    feedbackMessage.value = `已导入 ${result.imported} 条校验规则`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导入失败'
  } finally {
    isImporting.value = false
    input.value = ''
  }
}

onMounted(async () => {
  await loadRules()
})
</script>

<style scoped>
.rule-toolbar {
  margin-bottom: 22px;
}

.file-input {
  display: none;
}

.rule-note {
  margin: 18px 0 0;
  color: #64748b;
  font-size: 14px;
}

.level-list {
  display: inline-block;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.regex-test-panel {
  display: grid;
  gap: 16px;
}

.regex-test-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #f8fbff;
}

.regex-test-header h3 {
  margin: 0 0 6px;
  font-size: 18px;
}

.regex-test-header p {
  margin: 0;
  color: #64748b;
}

.regex-test-frame-wrap {
  width: 100%;
  min-height: 720px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: #fff;
}

.regex-test-frame {
  width: 100%;
  min-height: 820px;
  margin-top: -86px;
  border: 0;
  background: #fff;
}

.rule-modal {
  width: min(760px, 100%);
}

.rule-form {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 16px;
  margin: 20px 0;
}

.rule-form label {
  display: grid;
  gap: 8px;
}

.pattern-field,
.levels-field {
  grid-column: 1 / -1;
}

.pattern-field .textarea {
  min-height: 140px;
}

.levels-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 8px;
}

.level-option {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
}

.error-note {
  color: var(--danger);
  font-weight: 600;
}

.success-note {
  margin: 12px 0 0;
  color: #0f766e;
  font-weight: 700;
}

@media (max-width: 760px) {
  .rule-form,
  .levels-grid {
    grid-template-columns: 1fr;
  }

  .regex-test-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
