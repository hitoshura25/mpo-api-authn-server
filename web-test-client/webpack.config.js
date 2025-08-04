const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');

const isDevelopment = process.env.NODE_ENV !== 'production';

module.exports = {
  mode: isDevelopment ? 'development' : 'production',
  entry: './src/index.ts',
  devtool: isDevelopment ? 'inline-source-map' : 'source-map',
  devServer: {
    static: './dist',
    port: 8082,
    hot: true,
    open: true
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: isDevelopment ? 'ts-loader' : [
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
    filename: isDevelopment ? 'webauthn-client.dev.js' : 'umd/webauthn-client.umd.js',
    path: path.resolve(__dirname, 'dist'),
    clean: true,
    library: {
      name: 'WebAuthnClient',
      type: 'umd',
    },
    globalObject: 'this',
  },
  optimization: {
    minimize: !isDevelopment,
    minimizer: !isDevelopment ? [new TerserPlugin({
      terserOptions: {
        compress: {
          drop_console: false, // Keep console logs for debugging
        },
        format: {
          comments: false,
        },
      },
      extractComments: false,
    })] : [],
  },
  plugins: [
    new CleanWebpackPlugin(),
    ...(isDevelopment ? [
      new HtmlWebpackPlugin({
        template: './public/index.html',
        filename: 'index.html',
      })
    ] : []),
  ],
  externals: {
    '@simplewebauthn/browser': {
      commonjs: '@simplewebauthn/browser',
      commonjs2: '@simplewebauthn/browser',
      amd: '@simplewebauthn/browser',
      root: 'SimpleWebAuthnBrowser'
    }
  }
};