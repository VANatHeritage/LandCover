# LandscapePlots_ggplot.R
# Plot showing land cover changes over time.
# Used to summarize results table from LandscapeChange.py. This is an alternative to python-based LandscapePlots.py.
# Author: David Bucklin
# created on: 2023-05-01

# Load libraries
library(arcgisbinding)
library(dplyr)
library(ggplot2)
library(tidyr)
library(ggbreak)
library(scales)
arc.check_product()
dir.create("plots")
# file.nm <- "lc_change_2001_2019_wSilv"

# Load table
tab <- "lc_rclsGeneral_changeSummary_upd2021" # | lc_rclsGeneral_changeSummary
d0 <- arc.select(arc.open(paste0("C:/David/proc/NLCD_chg/nlcd_2019ed_LandCover_albers_rclsBarrens.gdb/", tab)))
head(d0)

# Pivot to a longer table
piv <- names(d0)[grepl("Area_ha_*", names(d0))]
d <- d0 %>% select(Value, CoverClass, starts_with("Area_ha_")) %>% 
  pivot_longer(cols = starts_with("Area_ha_"), names_to = "name", values_to = "Area_ha") %>%
  mutate(year = as.integer(substr(name, nchar(name)-3, nchar(name)))) %>% arrange(Value, year) %>%
  mutate(pct_change = ifelse(year != 2001, round(((Area_ha - lag(Area_ha)) / lag(Area_ha)) * 100, 2), NA), 
         label = as.character(ifelse(pct_change > 0, paste0("+", pct_change, "%"), paste0(pct_change, "%")))) # %>% filter(CoverClass != "Open Water") 

# Get full time period percent change for labels
cp <- d %>% group_by(CoverClass) %>% 
  summarize(x=median(year), y=median(Area_ha), 
            area_change = last(Area_ha) - first(Area_ha), 
            pct_change = round(((last(Area_ha) - first(Area_ha)) / first(Area_ha) *100) , 2)) %>%
  mutate(label = as.character(ifelse(pct_change > 0, paste0("+", pct_change, "%"), paste0(pct_change, "%"))))
print(cp)

# Set up factors (note order)
d$CoverClass <- factor(d$CoverClass, levels = cp$CoverClass[order(cp$y, decreasing=TRUE)])
cp$CoverClass <-  factor(cp$CoverClass, levels = cp$CoverClass[order(cp$y, decreasing=TRUE)])

class_col <- data.frame(cls = c("Natural", "Agriculture", "Developed", "Open Water", "Successional", "Harvested/Disturbed"),
                        col = c("DarkGreen", "GoldenRod", "DarkRed", "Blue", "LimeGreen", "lightcyan4"))

# ggplot(d, aes(x=year, y=Area_ha, fill=CoverClass)) + geom_area()  # area plot; another way to look at the data
g <- ggplot(d, aes(x=year, y=Area_ha, col=CoverClass)) + 
  geom_point(cex=2.5) + 
  geom_line(lwd=1) + 
  geom_text(aes(label=label, col=CoverClass), nudge_x = -0.1, nudge_y = -60000, cex=2.6,check_overlap = T) + # , col='black') +
  geom_text(data=cp, aes(x=x, y=y, label=label), nudge_x = 0.5, nudge_y = 90000, show.legend = F, cex = 4) + 
  scale_color_manual(labels = paste0(levels(cp$CoverClass), " "),  # this adds whitespace to labels so they space out horizontally.
                     values=class_col$col[match(levels(cp$CoverClass), class_col$cls)]) +
  labs(color=NULL) + # ,  caption="Source: Virginia Natural Heritage Program") + 
  scale_y_break(breaks=c(2250000, 6300000)) + # scale_y_break(c(1250000, 1900000)) + 
  # scale_y_break(breaks=c(2250000, 5600000)) + # scale_y_break(c(1250000, 1900000)) + 
  scale_y_continuous(position = "left", labels=label_number(accuracy=0.01, scale=1e-6), breaks=seq(200000, 6900000, 200000), limits = c(0, 6750000)) + 
  # scale_y_continuous(position = "left", labels=label_number(accuracy=0.01, scale=1e-6), breaks=seq(200000, 6900000, 200000), limits = c(0, 6000000)) + 
  scale_x_continuous(breaks=seq(2001, 2021, 2)) + 
  ggtitle("Land Cover in Virginia", "Based on the National Land Cover Database, 2021 edition") + xlab("Year") + ylab("Hectares (millions)") +
  theme_bw() + 
  theme(legend.margin = margin(0, 0, 0, 0), legend.position = "top", legend.text = element_text(size=10),
        # text = element_text(family="Open Sans"),
        panel.grid.major.x = element_blank(), panel.grid.minor.x = element_blank(), # this is hack to remove ticks from right side of plot 
        axis.text.y.right = element_blank(),axis.line.y.right = element_blank(),axis.ticks.y.right = element_blank()) + 
  guides(colour = guide_legend(nrow = 1))
g
ggsave(paste0("plots/", tab, "_plot.png"), g, width=8.5, height=6.6)  # size in inches
