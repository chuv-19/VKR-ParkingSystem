<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="onClose">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="register-title">
        <button type="button" class="modal__close" aria-label="Закрыть" @click="onClose">
          <X :size="20" />
        </button>
        <h2 id="register-title" class="modal__heading">
          <UserPlus :size="22" class="modal__heading-icon" aria-hidden="true" />
          Регистрация
        </h2>
        <p class="modal__hint">Создайте аккаунт, чтобы сохранять избранные парковки.</p>

        <p v-if="localError" class="modal__error" role="alert">{{ localError }}</p>

        <form class="form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="field__label">
              <Mail :size="16" aria-hidden="true" />
              Логин или email
            </span>
            <input
              v-model.trim="login"
              type="text"
              autocomplete="username"
              placeholder="name@example.com"
              class="field__input"
              :disabled="submitting"
              required
            />
          </label>
          <label class="field">
            <span class="field__label">
              <Lock :size="16" aria-hidden="true" />
              Пароль
            </span>
            <input
              v-model="password"
              type="password"
              autocomplete="new-password"
              placeholder="не менее 6 символов"
              class="field__input"
              :disabled="submitting"
              required
              minlength="6"
            />
          </label>
          <label class="field">
            <span class="field__label">
              <Lock :size="16" aria-hidden="true" />
              Повтор пароля
            </span>
            <input
              v-model="passwordRepeat"
              type="password"
              autocomplete="new-password"
              placeholder="ещё раз"
              class="field__input"
              :disabled="submitting"
              required
              minlength="6"
            />
          </label>
          <div class="actions">
            <button type="button" class="btn btn--ghost" :disabled="submitting" @click="onClose">
              Отмена
            </button>
            <button type="submit" class="btn btn--primary" :disabled="submitting">
              {{ submitting ? 'Создание…' : 'Создать аккаунт' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { Lock, Mail, UserPlus, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { registerRequest, type AuthOkResponse } from '../api/auth'

const props = defineProps<{
  /** Подставить логин из карточки входа при открытии */
  initialLogin?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success', payload: AuthOkResponse): void
}>()

const login = ref('')
const password = ref('')
const passwordRepeat = ref('')
const localError = ref<string | null>(null)
const submitting = ref(false)

function resetForm() {
  login.value = props.initialLogin?.trim() ?? ''
  password.value = ''
  passwordRepeat.value = ''
  localError.value = null
  submitting.value = false
}

onMounted(() => {
  resetForm()
})

function onClose() {
  emit('close')
}

async function onSubmit() {
  localError.value = null
  if (password.value !== passwordRepeat.value) {
    localError.value = 'Пароли не совпадают'
    return
  }
  submitting.value = true
  try {
    const data = await registerRequest(login.value, password.value)
    emit('success', data)
    emit('close')
  } catch (e) {
    localError.value = e instanceof Error ? e.message : 'Не удалось зарегистрироваться'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal {
  position: relative;
  width: min(420px, 100%);
  max-height: min(90vh, 640px);
  overflow: auto;
  background: #ffffff;
  border-radius: 14px;
  padding: 1.5rem;
  padding-top: 2.75rem;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
  border: 1px solid #e2e8f0;
}

.modal__close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: none;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  cursor: pointer;
}

.modal__close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.modal__heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.35rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.modal__heading-icon {
  flex-shrink: 0;
  color: #2563eb;
}

.modal__hint {
  margin: 0 0 1rem;
  font-size: 0.875rem;
  color: #64748b;
  line-height: 1.4;
}

.modal__error {
  margin: 0 0 0.75rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field__label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.field__label :deep(svg) {
  flex-shrink: 0;
  color: #64748b;
}

.field__input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.55rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.95rem;
}

.field__input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.field__input:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.35rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 1rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn--ghost {
  background: #fff;
  color: #334155;
  border-color: #cbd5e1;
}

.btn--ghost:hover:not(:disabled) {
  background: #f8fafc;
}

.btn--primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.btn--primary:hover:not(:disabled) {
  background: #1d4ed8;
}
</style>
