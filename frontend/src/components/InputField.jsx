import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import './InputField.css';

export default function InputField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  error,
  placeholder,
  autoComplete,
  required,
  hint,
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className={`field ${error ? 'field--error' : ''}`}>
      {label && (
        <label className="field__label" htmlFor={name}>
          {label}{required && <span className="field__required" aria-hidden="true"> *</span>}
        </label>
      )}
      <div className="field__wrapper">
        <input
          id={name}
          name={name}
          type={inputType}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          className="field__input"
          aria-describedby={error ? `${name}-error` : hint ? `${name}-hint` : undefined}
          aria-invalid={!!error}
        />
        {isPassword && (
          <button
            type="button"
            className="field__eye"
            onClick={() => setShowPassword((s) => !s)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
      {hint && !error && <p id={`${name}-hint`} className="field__hint">{hint}</p>}
      {error && <p id={`${name}-error`} className="field__error" role="alert">{error}</p>}
    </div>
  );
}
