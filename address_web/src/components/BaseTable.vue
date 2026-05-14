<template>
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key" scope="col" :style="{ width: column.width }">
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="getRowKey(row)">
          <td
            v-for="column in columns"
            :key="column.key"
            :class="column.className"
          >
            <slot :name="`cell-${column.key}`" :row="row">
              {{ row[column.key] }}
            </slot>
          </td>
        </tr>
        <tr v-if="rows.length === 0">
          <td class="empty-cell" :colspan="columns.length || 1">暂无数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import type { TableColumn } from '../types'

const props = defineProps<{
  columns: TableColumn[]
  rows: T[]
  rowKey?: keyof T | ((row: T) => string)
}>()

const getRowKey = (row: T) => {
  if (typeof props.rowKey === 'function') {
    return props.rowKey(row)
  }

  if (props.rowKey) {
    return String(row[props.rowKey])
  }

  return JSON.stringify(row)
}
</script>
