const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');

module.exports = {
  mode: 'production',
  entry: './src/index.ts',
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: [
          {
            loader: 'babel-loader',
            options: {
              presets: [
                ['@babel/preset-env', {
                  targets: {
                    browsers: ['> 1%', 'last 2 versions', 'ie >= 11']
                  },
                  modules: false
                }]
              ]
            }
          },
          'ts-loader'
        ],
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
  },
  output: {
    filename: 'webauthn-client.umd.js',
    path: path.resolve(__dirname, 'dist/umd'),
    clean: true,
    library: {
      name: 'WebAuthnClient',
      type: 'umd',
    },
    globalObject: 'this',
  },
  optimization: {
    minimize: true,
    minimizer: [new TerserPlugin({
      terserOptions: {
        compress: {
          drop_console: false, // Keep console logs for debugging
        },
        format: {
          comments: false,
        },
      },
      extractComments: false,
    })],
  },
  externals: {
    '@simplewebauthn/browser': {
      commonjs: '@simplewebauthn/browser',
      commonjs2: '@simplewebauthn/browser',
      amd: '@simplewebauthn/browser',
      root: 'SimpleWebAuthnBrowser'
    }
  },
  // Also create a modern ES2020 version
  ...(process.env.MODERN_BUILD && {
    output: {
      filename: 'webauthn-client.modern.js',
      path: path.resolve(__dirname, 'dist/umd'),
      library: {
        name: 'WebAuthnClient',
        type: 'umd',
      },
      globalObject: 'this',
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: 'ts-loader',
          exclude: /node_modules/,
        },
      ],
    },
  })
};