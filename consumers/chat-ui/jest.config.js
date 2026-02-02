const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './',
});

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/.next/'],
  collectCoverageFrom: [
    'src/lib/hooks/**/*.{ts,tsx}',
    'src/components/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/index.ts',
  ],
  coverageThreshold: {
    // Thresholds for new localStorage features (high coverage expected)
    './src/lib/hooks/useLocalStorage.ts': {
      branches: 80,
      functions: 90,
      lines: 80,
      statements: 80,
    },
    './src/lib/hooks/useTheme.ts': {
      branches: 70,
      functions: 80,
      lines: 80,
      statements: 80,
    },
    './src/lib/hooks/useSearchHistory.ts': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
    './src/lib/hooks/useBookmarks.ts': {
      branches: 70,
      functions: 90,
      lines: 90,
      statements: 90,
    },
  },
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig);
