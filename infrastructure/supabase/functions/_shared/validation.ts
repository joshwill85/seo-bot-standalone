import { ValidationError, ValidationAppError } from './types.ts'

export interface ValidationRule<T = any> {
  validate: (value: T) => boolean
  message: string
}

export interface FieldValidation {
  field: string
  rules: ValidationRule[]
  required?: boolean
}

export function validateRequired(value: any): boolean {
  if (value === null || value === undefined) return false
  if (typeof value === 'string' && value.trim().length === 0) return false
  return true
}

export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function validateUrl(url: string): boolean {
  try {
    new URL(url.startsWith('http') ? url : `https://${url}`)
    return true
  } catch {
    return false
  }
}

export function validatePhone(phone: string): boolean {
  const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/
  return phoneRegex.test(phone)
}

export function validatePassword(password: string): boolean {
  return password.length >= 8 && 
         /(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)
}

export function validateEnum<T extends string>(
  value: string, 
  allowedValues: readonly T[]
): value is T {
  return allowedValues.includes(value as T)
}

export function validateObject(data: Record<string, any>, validations: FieldValidation[]) {
  const errors: ValidationError[] = []

  for (const validation of validations) {
    const { field, rules, required = false } = validation
    const value = data[field]

    // Check required
    if (required && !validateRequired(value)) {
      errors.push({
        field,
        message: `${field} is required`
      })
      continue
    }

    // Skip validation if field is optional and empty
    if (!required && !validateRequired(value)) {
      continue
    }

    // Run validation rules
    for (const rule of rules) {
      if (!rule.validate(value)) {
        errors.push({
          field,
          message: rule.message
        })
        break // Only show first error per field
      }
    }
  }

  if (errors.length > 0) {
    throw new ValidationAppError('Validation failed', errors)
  }
}

// Business form validation
export function validateBusinessData(data: any) {
  validateObject(data, [
    {
      field: 'business_name',
      required: true,
      rules: [
        {
          validate: (value: string) => value.length >= 2 && value.length <= 200,
          message: 'Business name must be between 2 and 200 characters'
        }
      ]
    },
    {
      field: 'website_url',
      required: false,
      rules: [
        {
          validate: validateUrl,
          message: 'Website URL must be a valid URL'
        }
      ]
    },
    {
      field: 'city',
      required: true,
      rules: [
        {
          validate: (value: string) => value.length >= 2 && value.length <= 100,
          message: 'City must be between 2 and 100 characters'
        }
      ]
    },
    {
      field: 'state',
      required: false,
      rules: [
        {
          validate: (value: string) => value.length <= 50,
          message: 'State must be 50 characters or less'
        }
      ]
    },
    {
      field: 'plan_tier',
      required: true,
      rules: [
        {
          validate: (value: string) => validateEnum(value, ['starter', 'professional', 'enterprise']),
          message: 'Plan tier must be starter, professional, or enterprise'
        }
      ]
    },
    {
      field: 'business_type',
      required: false,
      rules: [
        {
          validate: (value: string) => validateEnum(value, ['local', 'national', 'ecommerce']),
          message: 'Business type must be local, national, or ecommerce'
        }
      ]
    },
    {
      field: 'phone',
      required: false,
      rules: [
        {
          validate: validatePhone,
          message: 'Phone number must be a valid phone number'
        }
      ]
    }
  ])
}

// User registration validation
export function validateUserRegistration(data: any) {
  validateObject(data, [
    {
      field: 'email',
      required: true,
      rules: [
        {
          validate: validateEmail,
          message: 'Email must be a valid email address'
        }
      ]
    },
    {
      field: 'password',
      required: true,
      rules: [
        {
          validate: validatePassword,
          message: 'Password must be at least 8 characters with uppercase, lowercase, and number'
        }
      ]
    },
    {
      field: 'first_name',
      required: true,
      rules: [
        {
          validate: (value: string) => value.length >= 1 && value.length <= 50,
          message: 'First name must be between 1 and 50 characters'
        }
      ]
    },
    {
      field: 'last_name',
      required: true,
      rules: [
        {
          validate: (value: string) => value.length >= 1 && value.length <= 50,
          message: 'Last name must be between 1 and 50 characters'
        }
      ]
    },
    {
      field: 'phone',
      required: false,
      rules: [
        {
          validate: validatePhone,
          message: 'Phone number must be a valid phone number'
        }
      ]
    }
  ])
}

// SEO report validation
export function validateSEOReportData(data: any) {
  validateObject(data, [
    {
      field: 'business_id',
      required: true,
      rules: [
        {
          validate: (value: number) => Number.isInteger(value) && value > 0,
          message: 'Business ID must be a positive integer'
        }
      ]
    },
    {
      field: 'report_type',
      required: true,
      rules: [
        {
          validate: (value: string) => validateEnum(value, [
            'full_audit', 'keyword_research', 'serp_analysis', 
            'performance_audit', 'accessibility_audit', 'content_analysis'
          ]),
          message: 'Invalid report type'
        }
      ]
    }
  ])
}