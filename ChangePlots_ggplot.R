# Load libraries
library(arcgisbinding)
library(dplyr)
library(ggplot2)
library(tidyr)
library(ggbreak)
library(scales)
arc.check_product()
dir.create("plots")

# Load table
gdb <- arc.open("C:/David/proc/NLCD_chg/nlcd2019ed_changeDetection.gdb")
ls <- gdb@children$RasterDataset[grepl("lc_allChange_", gdb@children$RasterDataset)]

# For specific time period selection
include <-"2001_2019|2001_2011|2011_2019"
ls <- ls[grepl(include, ls)]

bla <- list()
for (l in ls) {
  d0 <- arc.raster(arc.open(paste0(gdb@path, "/", l)))
  df <- d0$attribute_table()
  df$data <- l
  bla[[l]] <- df
}
d <- bind_rows(bla) %>% mutate(chg_years = gsub("_", "-", substr(data, nchar(data)-8, nchar(data))))
table(d$start_class, d$start_class_name)
table(d$chg_years)
# END HEADER


# classes to look at
cls <- c(41, 42, 43, 52, 90)   #  c(41, 42, 43, 52, 90)
cls_name <- "Forest"
out.nm <- paste0(cls_name, "_change_tofrom_2001_2011_2019")

# Sucessional reassign
d$start_class[d$start_class %in% c(56, 75)] <- 61
d$end_class[d$end_class %in% c(56, 75)] <- 61

# Filter/reassign class values
exclude <- c(NULL) # c("2011-2019")
d1 <- d %>% filter((start_class %in% cls & !end_class %in% cls) | (end_class %in% cls & !start_class %in% cls), 
                  !chg_years %in% exclude) %>% 
  mutate(gen_start = ifelse(start_class %in% cls, 99, as.character(trunc(start_class / 10) * 10)), 
         gen_end = ifelse(end_class %in% cls, 99, as.character(trunc(end_class / 10) * 10))) 

# Summary of class change
d2 <- d1 %>%
  group_by(gen_start, gen_end, chg_years) %>% summarise(hectares = sum(Count) * 900 / 10000) %>%
  arrange(chg_years, desc(hectares)) %>% mutate(to_from=ifelse(gen_start == 99, "Loss", "Gain"), 
                                                   chg_class = ifelse(gen_start == 99, gen_end, gen_start)) %>% 
  arrange(chg_years, desc(to_from), chg_class) # %>% filter(!chg_class %in% c(50, 60, 70)) # optional: exclude water/herbaceous change 
d2$to_from <- factor(d2$to_from, levels = c("Loss", "Gain"))
d2$chg_years <- factor(d2$chg_years, levels = sort(unique(d2$chg_years)))
d2$chg_class <- factor(d2$chg_class, levels=c(20, 80, 30, 40, 50, 60, 70, 90, 10, 99), 
                       labels = c("Developed", "Agriculture", "Barren", "Forest", "Shrub/Scrub", "Successional", "Herbaceous", "Wetlands", "Water", cls_name))

col_vec <- c("Forest" = "DarkGreen", "Agriculture" = "gold3", "Developed" = "purple", "Water" = "skyblue1", 
                  "Barren" = "grey70", "Shrub/Scrub" = "darkseagreen4", "Successional" = "lightgreen", "Herbaceous" = "yellowgreen", "Wetlands" = "aquamarine4")

# stacked barplot
# g <- ggplot(d2) + geom_bar(aes(x=to_from, y=hectares, fill=chg_class), stat = "identity") +
#   scale_fill_manual(values=col_vec) +
#   facet_wrap("chg_years", nrow=1) + xlab("Change type") + ylab("Hectares") + 
#   labs(fill=paste0(cls_name, " loss to \n/ gain from:"),caption=paste0(cls_name, " class values: (", paste(cls, collapse = ", "), ")")) + 
#   ggtitle(paste0(cls_name, " change in Virginia, 2001-2019"))
# g
# ggsave(paste0("plots/", out.nm, ".png"), g, width=9, height=6)  # size in inches

# NET (+/-)
d2.net <- d2 %>% mutate(hectares = ifelse(to_from=="Loss", -hectares, hectares)) %>%
  group_by(chg_years, chg_class) %>% summarise(ha = sum(hectares))
d2.net$grp <- ifelse(!d2.net$chg_years %in% c("2001-2019"), " Intermediate periods", "Full period")

g <- ggplot(d2.net) + geom_bar(aes(x=chg_years, y=ha, fill=chg_class), position = "dodge", stat = "identity") +
  scale_fill_manual(values=col_vec) +
  xlab("Time period") + ylab("Hectares") +
  facet_grid(cols=vars(grp), scales = "free_x", space = "free") + 
  labs(fill=paste0('Net ', cls_name, ' lost \nto / gained from:'), caption=paste0(cls_name, " class values: (", paste(cls, collapse = ", "), ")")) + 
  ggtitle(paste0(cls_name, " change in Virginia, 2001-2019"), 
          subtitle = paste0("Net gain/loss of ", cls_name, " land cover")) +
  scale_y_continuous(labels=label_number(accuracy=1, scale=1, big.mark = ",", style_positive = "plus"), breaks=seq(-100000, 25000, 25000)) + 
  theme_bw()
g
ggsave(paste0("plots/", out.nm, "_net.png"), g, width=8, height=5)  # size in inches



############## 

# NOT USING BELOW
file.nm <- "chg_forest_tofrom_2001_2019_tab"

# Load table
d0 <- arc.select(arc.open(paste0("C:/David/proc/NLCD_chg/nlcd2019ed_changeDetection.gdb/", file.nm)))
d1 <- d0 %>% filter(!Value %in% c(0, 1), startsWith(change_type, "Forest to")) %>%
  arrange(desc(area_ha))

ggplot(d1, aes(x = "", y = area_ha, fill = change_type)) +
  geom_col() +
  coord_polar(theta = "y")

d2 <- d0 %>% filter(!Value %in% c(0, 1), !startsWith(change_type, "Forest to")) %>%
  arrange(desc(area_ha))

ggplot(d2, aes(x = "", y = area_ha, fill = change_type)) +
  geom_col() +
  coord_polar(theta = "y")


d1 <- d0 %>% filter(!Value %in% c(0, 1)) %>% mutate(general = round(Value, -1), 
                                                    type=ifelse(startsWith(change_type, "Forest to"), "Forest loss", "Forest gain")) %>%
  arrange(desc(area_ha))

ggplot(d1) + geom_bar(aes(x=type, y=area_ha, fill=change_type), stat="identity")

