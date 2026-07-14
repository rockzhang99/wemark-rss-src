<template>
  <a-modal v-model:visible="visible" title="导出设置" @ok="handleOk" @cancel="handleCancel">
    <a-form :model="form">
      <a-form-item label="导出范围" field="scope">
        <a-select v-model="form.scope" placeholder="请选择导出范围" disabled>
          <a-option value="all">指定页数</a-option>
          <a-option value="selected">已选文章</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="导出格式" field="format">
        <a-select v-model="form.format" placeholder="请选择导出格式" multiple>
          <a-option value="csv">Excel列表</a-option>
          <a-option value="md">MarkDown</a-option>
          <a-option value="json">JSON附加信息</a-option>
        </a-select>
      </a-form-item>
      <a-form-item label="导出页数" field="limit" v-if="form.scope === 'all' || form.scope === 'current'">
        <a-input-number v-model="form.page_count" :min="1" :max="10000" />
      </a-form-item>
      <a-form-item label="文件名" field="zip_filename">
        <a-input v-model="form.zip_filename" placeholder="请输入导出文件名（可选）" />
      </a-form-item>
      <a-form-item label="导出选项" field="options">
        <a-space direction="vertical">
          <a-checkbox v-model="form.add_title">添加标题</a-checkbox>
          <a-checkbox v-model="form.remove_images">移除图片</a-checkbox>
          <a-checkbox v-model="form.remove_links">移除链接</a-checkbox>
        </a-space>
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- 导出进度弹窗 -->
  <a-modal
    v-model:visible="progressVisible"
    title="导出进度"
    :footer="false"
    :closable="exportDone || exportFailed"
    :mask-closable="false"
  >
    <div style="padding: 8px 0;">
      <a-progress
        :percent="exportStatus.percent"
        :status="exportFailed ? 'error' : (exportDone ? 'success' : 'normal')"
      />
      <p style="margin-top: 12px; color: var(--color-text-2);">
        <template v-if="exportStatus.status === 'running'">
          正在导出文章：已处理 {{ exportStatus.processed }} / {{ exportStatus.total || '?' }} 篇
        </template>
        <template v-else-if="exportDone">
          导出完成！文件：{{ exportStatus.filename }}
        </template>
        <template v-else-if="exportFailed">
          导出失败：{{ exportStatus.error || '未知错误' }}
        </template>
        <template v-else>
          等待开始…
        </template>
      </p>
      <a-button v-if="exportDone" type="primary" long @click="goToRecords">前往导出记录</a-button>
      <a-button v-if="exportDone || exportFailed" style="margin-top: 8px;" long @click="closeProgress">
        关闭
      </a-button>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Message } from '@arco-design/web-vue';
import { exportArticles, getExportStatus } from '@/api/tools';
import { useRouter } from 'vue-router';

const router = useRouter();

const visible = ref(false);
const form = ref({
  scope: 'all',
  format: ['json', 'csv', 'md'],
  page_count: 10,
  mp_id: '',
  ids: [],
  add_title: true,
  remove_images: false,
  remove_links: false,
  zip_filename: '',
});

const emit = defineEmits(['confirm']);

const show = (mp_id: string, ids: any, mp_name?: string) => {
  visible.value = true;
  form.value.mp_id = mp_id;
  console.log(ids);
  form.value.scope = ids && ids.length > 0 ? 'selected' : 'all';
  form.value.ids = ids;

  // 如果提供了公众号名称，设置默认文件名
  if (mp_name && mp_name !== '全部') {
    form.value.zip_filename = `${mp_name}_文章.zip`;
  } else {
    form.value.zip_filename = '全部文章.zip';
  }
};

const hide = () => {
  visible.value = false;
};

const handleOk = () => {
  SubmitExport(form.value);
  emit('confirm', form.value);
  hide();
};
const SubmitExport = async (params: any) => {
  try {
    const result = await exportArticles(params);
    console.log('导出成功:', result);
    Message.success(result.message || '导出任务已启动');
    // 启动进度轮询，前端实时展示导出进度
    startPolling(params.mp_id);
  } catch (error) {
    console.error('导出失败:', error);
  }
};
const handleCancel = () => {
  hide();
};

// ===== 导出进度轮询 =====
const progressVisible = ref(false);
const exportStatus = ref({
  status: 'running',
  percent: 0,
  processed: 0,
  total: 0,
  filename: '',
  error: ''
});
const exportDone = computed(() => exportStatus.value.status === 'done');
const exportFailed = computed(() => exportStatus.value.status === 'failed');
let pollTimer: any = null;
// 注意：导出“全部”公众号时 mp_id 为空字符串 ''，不能用真值判断，否则轮询会被跳过
let currentMpId: string | null = null;
let polling = false;

const startPolling = (mp_id: string) => {
  currentMpId = mp_id ?? '';
  polling = true;
  exportStatus.value = {
    status: 'running',
    percent: 0,
    processed: 0,
    total: 0,
    filename: '',
    error: ''
  };
  progressVisible.value = true;
  pollStatus();
  pollTimer = setInterval(pollStatus, 1500);
};

const pollStatus = async () => {
  if (!polling || currentMpId === null) return;
  try {
    const res = await getExportStatus({ mp_id: currentMpId });
    const data = (res && (res as any).data) || res || {};
    exportStatus.value = { ...exportStatus.value, ...data };
    if (data.status === 'done' || data.status === 'failed') {
      stopPolling();
      if (data.status === 'done') {
        Message.success('导出完成');
      }
    }
  } catch (e) {
    // 网络异常时停止轮询，避免死循环
    stopPolling();
  }
};

const stopPolling = () => {
  polling = false;
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const goToRecords = () => {
  closeProgress();
  router.push('/export/records');
};

const closeProgress = () => {
  progressVisible.value = false;
  stopPolling();
};

defineExpose({
  show,
  hide,
});
</script>
