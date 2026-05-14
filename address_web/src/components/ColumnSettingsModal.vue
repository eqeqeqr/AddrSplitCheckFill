<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal-card">
      <div class="modal-body">
        <div class="modal-header">
          <div>
            <h3>设置列显示</h3>
            <p>{{ mode === 'raw' ? '原始字段按 PDF 标注字段自由勾选' : '8级和11级为固定接口字段，不支持任意勾选' }}</p>
          </div>
          <button type="button" class="close-button" aria-label="关闭列设置弹窗" @click="$emit('close')">
            <X :size="18" aria-hidden="true" />
          </button>
        </div>

        <div class="modal-form">
          <label class="modal-field">
            <span class="field-label">列方案</span>
            <select
              class="select"
              :value="mode"
              @change="$emit('update:mode', ($event.target as HTMLSelectElement).value as ColumnMode)"
            >
              <option v-for="item in modes" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>

        </div>

        <div class="column-list">
          <div v-for="item in modelValue" :key="item.key" class="column-row">
            <label class="check-label">
              <input
                :checked="item.visible"
                :disabled="item.fixed || mode !== 'raw'"
                type="checkbox"
                @change="toggleVisible(item.key)"
              />
              <span>
                {{ item.label }}
                <small v-if="item.description">{{ item.description }}</small>
              </span>
            </label>
            <span class="order-hint">{{ item.fixed || mode !== 'raw' ? '固定' : '可选' }}</span>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="ghost-button" @click.stop="$emit('close')">取消</button>
          <button type="button" class="primary-button" @click.stop="$emit('confirm')">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { X } from 'lucide-vue-next'
import type { ColumnMode, ColumnSettingItem } from '../types'

const props = defineProps<{
  modelValue: ColumnSettingItem[]
  mode: ColumnMode
  modes: Array<{ label: string; value: ColumnMode; description: string }>
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: ColumnSettingItem[]): void
  (event: 'update:mode', value: ColumnMode): void
  (event: 'close'): void
  (event: 'confirm'): void
}>()

const toggleVisible = (key: ColumnSettingItem['key']) => {
  if (props.mode !== 'raw') {
    return
  }

  const next = props.modelValue.map((item) =>
    item.key === key && !item.fixed ? { ...item, visible: !item.visible } : item,
  )

  emit('update:modelValue', next)
}
</script>
