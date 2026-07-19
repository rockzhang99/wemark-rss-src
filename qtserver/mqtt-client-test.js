const mqtt = require('mqtt');

class MQTTClientTest {
    constructor(options = {}) {
        this.host = options.host || 'localhost';
        this.port = options.port || 1883;
        this.wsPort = options.wsPort || 8083;
        this.clientId = options.clientId || `test_client_${Date.now()}`;
        
        this.mqttClient = null;
        this.wsClient = null;
        this.testResults = [];
        
        // console.log('MQTT客户端测试初始化:');
        // console.log(`- 主机: ${this.host}`);
        // console.log(`- MQTT端口: ${this.port}`);
        // console.log(`- WebSocket端口: ${this.wsPort}`);
        // console.log(`- 客户端ID: ${this.clientId}`);
    }
    
    // 测试MQTT连接
    async testMQTTConnection() {
        // console.log('\n=== 测试MQTT连接 ===');
        
        return new Promise((resolve, reject) => {
            try {
                const url = `mqtt://${this.host}:${this.port}`;
                this.mqttClient = mqtt.connect(url, {
                    clientId: this.clientId,
                    clean: true,
                    connectTimeout: 4000,
                    reconnectPeriod: 1000
                });
                
                this.mqttClient.on('connect', () => {
                    // console.log('✅ MQTT连接成功');
                    this.testResults.push({ type: 'mqtt_connect', success: true, message: 'MQTT连接成功' });
                    resolve(true);
                });
                
                this.mqttClient.on('error', (error) => {
                    console.error('❌ MQTT连接失败:', error.message);
                    this.testResults.push({ type: 'mqtt_connect', success: false, message: `MQTT连接失败: ${error.message}` });
                    reject(error);
                });
                
                this.mqttClient.on('close', () => {
                    // console.log('MQTT连接已关闭');
                });
                
            } catch (error) {
                console.error('❌ MQTT连接异常:', error.message);
                this.testResults.push({ type: 'mqtt_connect', success: false, message: `MQTT连接异常: ${error.message}` });
                reject(error);
            }
        });
    }
    
    // 测试MQTT消息发布和订阅
    async testMQTTMessaging() {
        console.log('\n=== 测试MQTT消息收发 ===');
        
        if (!this.mqttClient || !this.mqttClient.connected) {
            // console.log('❌ 请先建立MQTT连接');
            return false;
        }
        
        const testTopic = 'test/topic';
        const testMessage = `测试消息 ${new Date().toISOString()}`;
        
        return new Promise((resolve) => {
            let messageReceived = false;
            
            // 订阅测试主题
            this.mqttClient.subscribe(testTopic, (err) => {
                if (err) {
                    console.error('❌ 订阅失败:', err.message);
                    this.testResults.push({ type: 'mqtt_subscribe', success: false, message: `订阅失败: ${err.message}` });
                    resolve(false);
                    return;
                }
                
                // console.log('✅ 订阅成功:', testTopic);
                this.testResults.push({ type: 'mqtt_subscribe', success: true, message: '订阅成功' });
                
                // 设置消息接收监听
                this.mqttClient.on('message', (topic, message) => {
                    if (topic === testTopic) {
                        messageReceived = true;
                        console.log('✅ 收到消息:', message.toString());
                        this.testResults.push({ 
                            type: 'mqtt_message_receive', 
                            success: true, 
                            message: `收到消息: ${message.toString()}` 
                        });
                        
                        // 取消订阅
                        this.mqttClient.unsubscribe(testTopic, (unsubErr) => {
                            if (unsubErr) {
                                // console.error('取消订阅失败:', unsubErr.message);
                            } else {
                                // console.log('✅ 取消订阅成功');
                            }
                            resolve(true);
                        });
                    }
                });
                
                // 发布测试消息
                setTimeout(() => {
                    this.mqttClient.publish(testTopic, testMessage, (pubErr) => {
                        if (pubErr) {
                            console.error('❌ 发布失败:', pubErr.message);
                            this.testResults.push({ type: 'mqtt_publish', success: false, message: `发布失败: ${pubErr.message}` });
                            resolve(false);
                        } else {
                            // console.log('✅ 发布成功:', testMessage);
                            this.testResults.push({ type: 'mqtt_publish', success: true, message: '发布成功' });
                        }
                    });
                }, 100);
                
                // 设置超时
                setTimeout(() => {
                    if (!messageReceived) {
                        console.error('❌ 消息接收超时');
                        this.testResults.push({ type: 'mqtt_message_receive', success: false, message: '消息接收超时' });
                        resolve(false);
                    }
                }, 5000);
            });
        });
    }
    
    // 测试WebSocket MQTT连接
    async testWebSocketMQTT() {
        // console.log('\n=== 测试WebSocket MQTT连接 ===');
        
        return new Promise((resolve) => {
            try {
                const WebSocket = require('ws');
                const wsUrl = `ws://${this.host}:${this.wsPort}`;
                
                this.wsClient = new WebSocket(wsUrl);
                
                this.wsClient.on('open', () => {
                    // console.log('✅ WebSocket连接成功');
                    this.testResults.push({ type: 'ws_connect', success: true, message: 'WebSocket连接成功' });
                    
                    // 测试WebSocket消息
                    this.testWebSocketMessaging().then(resolve);
                });
                
                this.wsClient.on('error', (error) => {
                    console.error('❌ WebSocket连接失败:', error.message);
                    this.testResults.push({ type: 'ws_connect', success: false, message: `WebSocket连接失败: ${error.message}` });
                    resolve(false);
                });
                
                this.wsClient.on('close', () => {
                    // console.log('WebSocket连接已关闭');
                });
                
            } catch (error) {
                console.error('❌ WebSocket连接异常:', error.message);
                this.testResults.push({ type: 'ws_connect', success: false, message: `WebSocket连接异常: ${error.message}` });
                resolve(false);
            }
        });
    }
    
    // 测试WebSocket消息收发
    async testWebSocketMessaging() {
        console.log('\n=== 测试WebSocket消息收发 ===');
        
        const testTopic = 'test/ws/topic';
        const testMessage = `WebSocket测试消息 ${new Date().toISOString()}`;
        
        return new Promise((resolve) => {
            let messageReceived = false;
            
            // 订阅主题
            this.wsClient.send(JSON.stringify({
                type: 'subscribe',
                topic: testTopic
            }));
            
            // 监听消息
            this.wsClient.on('message', (data) => {
                try {
                    const message = JSON.parse(data);
                    
                    if (message.type === 'suback' && message.topic === testTopic) {
                        // console.log('✅ WebSocket订阅成功');
                        this.testResults.push({ type: 'ws_subscribe', success: true, message: 'WebSocket订阅成功' });
                        
                        // 发布消息
                        setTimeout(() => {
                            this.wsClient.send(JSON.stringify({
                                type: 'publish',
                                topic: testTopic,
                                payload: testMessage
                            }));
                            // console.log('✅ WebSocket发布成功:', testMessage);
                            this.testResults.push({ type: 'ws_publish', success: true, message: 'WebSocket发布成功' });
                        }, 100);
                        
                    } else if (message.type === 'message' && message.topic === testTopic) {
                        messageReceived = true;
                        console.log('✅ WebSocket收到消息:', message.payload);
                        this.testResults.push({ 
                            type: 'ws_message_receive', 
                            success: true, 
                            message: `WebSocket收到消息: ${message.payload}` 
                        });
                        
                        // 取消订阅
                        this.wsClient.send(JSON.stringify({
                            type: 'unsubscribe',
                            topic: testTopic
                        }));
                        
                        resolve(true);
                    }
                    
                } catch (error) {
                    console.error('解析WebSocket消息错误:', error);
                }
            });
            
            // 设置超时
            setTimeout(() => {
                if (!messageReceived) {
                    console.error('❌ WebSocket消息接收超时');
                    this.testResults.push({ type: 'ws_message_receive', success: false, message: 'WebSocket消息接收超时' });
                    resolve(false);
                }
            }, 5000);
        });
    }
    
    // 运行所有测试
    async runAllTests() {
        // console.log('🚀 开始运行MQTT客户端测试...\n');
        
        try {
            // 测试MQTT连接
            await this.testMQTTConnection();
            
            // 测试MQTT消息收发
            await this.testMQTTMessaging();
            
            // 测试WebSocket MQTT
            await this.testWebSocketMQTT();
            
        } catch (error) {
            console.error('测试过程中出现错误:', error.message);
        } finally {
            // 清理连接
            this.cleanup();
            
            // 输出测试结果
            this.printTestResults();
        }
    }
    
    // 清理连接
    cleanup() {
        if (this.mqttClient) {
            this.mqttClient.end();
            // console.log('\n🔌 MQTT连接已关闭');
        }
        
        if (this.wsClient) {
            this.wsClient.close();
            // console.log('🔌 WebSocket连接已关闭');
        }
    }
    
    // 打印测试结果
    printTestResults() {
        // console.log('\n📊 === 测试结果汇总 ===');
        
        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.success).length;
        const failedTests = totalTests - passedTests;
        
        // console.log(`总计测试: ${totalTests}`);
        // console.log(`通过: ${passedTests} ✅`);
        // console.log(`失败: ${failedTests} ❌`);
        
        if (failedTests === 0) {
            // console.log('🎉 所有测试通过！');
        } else {
            // console.log('\n失败的测试:');
            this.testResults.filter(r => !r.success).forEach(r => {
                console.log(`❌ ${r.type}: ${r.message}`);
            });
        }
        
        console.log('\n详细的测试结果:');
        this.testResults.forEach(r => {
            const status = r.success ? '✅' : '❌';
            console.log(`${status} ${r.type}: ${r.message}`);
        });
    }
}

// 命令行使用
if (require.main === module) {
    const testClient = new MQTTClientTest();
    testClient.runAllTests().catch(error => {
        console.error('测试运行失败:', error);
        process.exit(1);
    });
}

module.exports = MQTTClientTest;