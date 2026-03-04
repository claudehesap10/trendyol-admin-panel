ALTER TABLE `scanHistory` ADD `telegramStatus` enum('pending','success','failed') DEFAULT 'pending';--> statement-breakpoint
ALTER TABLE `scanHistory` ADD `emailStatus` enum('pending','success','failed') DEFAULT 'pending';--> statement-breakpoint
ALTER TABLE `settings` ADD `smtpServer` varchar(255) DEFAULT 'smtp.gmail.com';--> statement-breakpoint
ALTER TABLE `settings` ADD `smtpPort` varchar(10) DEFAULT '587';--> statement-breakpoint
ALTER TABLE `settings` ADD `smtpEmail` varchar(255);--> statement-breakpoint
ALTER TABLE `settings` ADD `smtpPassword` text;--> statement-breakpoint
ALTER TABLE `settings` ADD `recipientEmails` text;