<template>
  <div class="auth-card">
    <h2 class="auth-card__title">
      <UserRound :size="22" class="auth-card__title-icon" aria-hidden="true" />
      Вход и регистрация
    </h2>
    <p v-if="errorMessage" class="auth-card__error" role="alert">{{ errorMessage }}</p>
    <form class="auth-form" @submit.prevent="emitLogin">
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
          :disabled="loading"
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
          autocomplete="current-password"
          placeholder="••••••••"
          class="field__input"
          :disabled="loading"
          required
        />
      </label>
      <div class="auth-actions">
        <button type="submit" class="btn btn--primary" :disabled="loading">
          <LogIn :size="18" aria-hidden="true" />
          {{ loading ? '…' : 'Войти' }}
        </button>
        <button type="button" class="btn btn--secondary" :disabled="loading" @click="emitOpenRegister">
          <UserPlus :size="18" aria-hidden="true" />
          Зарегистрироваться
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { Lock, LogIn, Mail, UserPlus, UserRound } from 'lucide-vue-next'
import { ref } from 'vue'

defineProps<{
  loading?: boolean
  errorMessage?: string | null
}>()

const emit = defineEmits<{
  (e: 'login', payload: { login: string; password: string }): void
  /** Открыть модальное окно регистрации (подсказка логина с карточки входа) */
  (e: 'open-register', payload: { loginHint: string }): void
}>()

const login = ref('')
const password = ref('')

function emitLogin() {
  emit('login', { login: login.value, password: password.value })
}

function emitOpenRegister() {
  emit('open-register', { loginHint: login.value })
}
</script>

<style scoped>
.auth-card {
  margin-top: 1.25rem;
  padding: 1.25rem 1.35rem;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
}

.auth-card__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.auth-card__title-icon {
  flex-shrink: 0;
  color: #2563eb;
}

.auth-card__error {
  margin: 0 0 0.75rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
  background: #ffffff;
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

.auth-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.25rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.5rem 1.1rem;
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

.btn svg {
  flex-shrink: 0;
}

.btn--primary {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}

.btn--primary:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

.btn--secondary {
  background: #ffffff;
  color: #1e293b;
  border-color: #cbd5e1;
}

.btn--secondary:hover:not(:disabled) {
  background: #f1f5f9;
}
</style>
